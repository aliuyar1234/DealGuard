"""Contract analysis service - core business logic."""

import asyncio
import time
from typing import Sequence
from uuid import UUID

from dealguard.infrastructure.ai.client import AnthropicClient
from dealguard.infrastructure.ai.prompts.contract_analysis_v1 import (
    ContractAnalysisPromptV1,
)
from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
    ContractAnalysis,
    ContractFinding,
    ContractType,
)
from dealguard.infrastructure.database.repositories.contract import (
    ContractAnalysisRepository,
    ContractRepository,
)
from dealguard.infrastructure.document.extractor import DocumentExtractor
from dealguard.infrastructure.storage.s3 import S3Storage
from dealguard.shared.context import get_tenant_context
from dealguard.shared.exceptions import AnalysisFailedError, NotFoundError, QuotaExceededError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


class ContractAnalysisService:
    """Service for contract analysis operations.

    This is the main entry point for contract-related business logic.
    It orchestrates document processing, AI analysis, and storage.
    """

    def __init__(
        self,
        contract_repo: ContractRepository,
        analysis_repo: ContractAnalysisRepository,
        ai_client: AnthropicClient,
        storage: S3Storage,
        extractor: DocumentExtractor,
    ) -> None:
        self.contract_repo = contract_repo
        self.analysis_repo = analysis_repo
        self.ai_client = ai_client
        self.storage = storage
        self.extractor = extractor

    async def upload_contract(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        contract_type: ContractType | None = None,
    ) -> Contract:
        """Upload a contract for analysis.

        Steps:
        1. Extract text from document
        2. Upload to S3
        3. Create contract record
        4. Queue for analysis

        Args:
            content: Raw file content
            filename: Original filename
            mime_type: MIME type of file
            contract_type: Optional contract type hint

        Returns:
            Created Contract with PENDING status
        """
        ctx = get_tenant_context()

        # TODO: Check quota
        # await self._check_quota(ctx.organization_id)

        # Extract text and metadata (run in thread to avoid blocking event loop)
        extracted = await asyncio.to_thread(
            self.extractor.extract, content, filename, mime_type
        )

        # Check for duplicate
        existing = await self.contract_repo.get_by_file_hash(extracted.file_hash)
        if existing:
            logger.info(
                "duplicate_contract_detected",
                file_hash=extracted.file_hash,
                existing_id=str(existing.id),
            )
            # Return existing contract instead of creating duplicate
            return existing

        # Upload to S3
        file_path, _ = await self.storage.upload(
            content=content,
            organization_id=ctx.organization_id,
            filename=filename,
            mime_type=mime_type,
        )

        # Create contract record (encryption handled automatically by model)
        contract = Contract(
            created_by=ctx.user_id,
            filename=filename,
            file_path=file_path,
            file_hash=extracted.file_hash,
            file_size_bytes=extracted.file_size_bytes,
            mime_type=mime_type,
            page_count=extracted.page_count,
            contract_type=contract_type,
            status=AnalysisStatus.PENDING,
            contract_text=extracted.text,  # Auto-encrypted by hybrid property
        )

        contract = await self.contract_repo.create(contract)

        logger.info(
            "contract_uploaded",
            contract_id=str(contract.id),
            filename=filename,
            page_count=extracted.page_count,
        )

        return contract

    async def perform_analysis(self, contract_id: UUID) -> ContractAnalysis:
        """Perform AI analysis on a contract.

        This is called by the background worker.

        Args:
            contract_id: ID of the contract to analyze

        Returns:
            ContractAnalysis with results
        """
        start_time = time.monotonic()

        # Get contract
        contract = await self.contract_repo.get_by_id(contract_id)
        if not contract:
            raise NotFoundError("Vertrag", str(contract_id))

        # Update status to processing
        await self.contract_repo.update_status(contract, AnalysisStatus.PROCESSING)

        try:
            # Run AI analysis
            prompt = ContractAnalysisPromptV1()
            # contract_type can be an enum or a string depending on how it was stored
            contract_type_str = None
            if contract.contract_type:
                contract_type_str = contract.contract_type.value if hasattr(contract.contract_type, 'value') else contract.contract_type

            # Get decrypted contract text (handled by hybrid property)
            ai_response = await self.ai_client.analyze_contract(
                contract_text=contract.contract_text,  # Auto-decrypted
                contract_type=contract_type_str,
                resource_id=contract_id,
            )

            # Parse response
            result = prompt.parse_response(ai_response.content)

            # Update contract type if detected
            if result.contract_type_detected and not contract.contract_type:
                contract.contract_type = self._map_contract_type(result.contract_type_detected)

            # Create analysis record
            processing_time_ms = int((time.monotonic() - start_time) * 1000)

            analysis = ContractAnalysis(
                contract_id=contract_id,
                risk_score=result.risk_score,
                risk_level=result.risk_level,
                summary=result.summary,
                recommendations=result.recommendations,
                processing_time_ms=processing_time_ms,
                ai_model_version=ai_response.model,
                prompt_version=prompt.version.version,
                input_tokens=ai_response.input_tokens,
                output_tokens=ai_response.output_tokens,
                cost_cents=ai_response.cost_cents,
            )

            # Create findings
            findings = [
                ContractFinding(
                    category=f.category,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    original_clause_text=f.original_clause_text,
                    clause_location=f.clause_location,
                    suggested_change=f.suggested_change,
                    market_comparison=f.market_comparison,
                )
                for f in result.findings
            ]

            # Save analysis with findings and update contract status atomically
            async with self.contract_repo.session.begin_nested():
                analysis = await self.analysis_repo.create_with_findings(analysis, findings)
                await self.contract_repo.update_status(contract, AnalysisStatus.COMPLETED)

            logger.info(
                "contract_analysis_completed",
                contract_id=str(contract_id),
                risk_score=result.risk_score,
                findings_count=len(findings),
                processing_time_ms=processing_time_ms,
            )

            return analysis

        except Exception as e:
            logger.exception(
                "contract_analysis_failed",
                contract_id=str(contract_id),
                error=str(e),
            )
            await self.contract_repo.update_status(
                contract,
                AnalysisStatus.FAILED,
                error_message=str(e),
            )
            raise AnalysisFailedError(f"Analyse fehlgeschlagen: {e}")

    async def get_contract(self, contract_id: UUID) -> Contract | None:
        """Get a contract by ID with analysis if available."""
        return await self.contract_repo.get_by_id_with_analysis(contract_id)

    async def list_contracts(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Contract]:
        """List contracts for the current organization."""
        return await self.contract_repo.get_all(limit=limit, offset=offset)

    async def delete_contract(self, contract_id: UUID) -> None:
        """Soft delete a contract."""
        contract = await self.contract_repo.get_by_id(contract_id)
        if not contract:
            raise NotFoundError("Vertrag", str(contract_id))

        # Delete from S3
        await self.storage.delete(contract.file_path)

        # Soft delete record
        await self.contract_repo.soft_delete(contract)

        logger.info("contract_deleted", contract_id=str(contract_id))

    def _map_contract_type(self, detected: str) -> ContractType:
        """Map AI-detected contract type to enum."""
        mapping = {
            "supplier": ContractType.SUPPLIER,
            "customer": ContractType.CUSTOMER,
            "service": ContractType.SERVICE,
            "nda": ContractType.NDA,
            "lease": ContractType.LEASE,
            "employment": ContractType.EMPLOYMENT,
            "license": ContractType.LICENSE,
        }
        return mapping.get(detected.lower(), ContractType.OTHER)
