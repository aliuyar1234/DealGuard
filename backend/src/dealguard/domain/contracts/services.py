"""Contract analysis service - core business logic."""

import time
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from dealguard.domain.contracts.ports import (
    AIClientPort,
    AIResponsePort,
    ContractAnalysisRepositoryPort,
    ContractRepositoryPort,
    DocumentExtractorPort,
    ExtractedDocument,
    StoragePort,
    TransactionPort,
)
from dealguard.infrastructure.ai.prompts.contract_analysis_v1 import (
    ContractAnalysisPromptV1,
    ContractAnalysisResult,
)
from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
    ContractAnalysis,
    ContractFinding,
    ContractType,
)
from dealguard.shared.concurrency import to_thread_limited
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
        contract_repo: ContractRepositoryPort,
        analysis_repo: ContractAnalysisRepositoryPort,
        ai_client: AIClientPort,
        storage: StoragePort,
        extractor: DocumentExtractorPort,
        transaction: TransactionPort,
    ) -> None:
        self.contract_repo = contract_repo
        self.analysis_repo = analysis_repo
        self.ai_client = ai_client
        self.storage = storage
        self.extractor = extractor
        self.transaction = transaction

    async def upload_contract(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        contract_type: ContractType | None = None,
        *,
        organization_id: UUID,
        user_id: UUID,
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
        # Extract text and metadata (run in thread to avoid blocking event loop)
        extracted = await self._extract_document(content, filename, mime_type)

        # Check for duplicate
        existing = await self.contract_repo.get_by_file_hash(extracted.file_hash)
        if existing:
            logger.info(
                "duplicate_contract_detected",
                file_hash=extracted.file_hash,
                existing_id=str(existing.id),
            )
            # Return existing contract instead of creating duplicate
            await self.contract_repo.replace_search_tokens(existing.id, extracted.text)
            return existing

        await self._check_quota(organization_id)

        # Release the DB connection before long-running network I/O (S3 upload).
        await self.transaction.commit()

        # Upload to S3
        file_path, _ = await self.storage.upload(
            content=content,
            organization_id=organization_id,
            filename=filename,
            mime_type=mime_type,
        )

        # Create contract record (encryption handled automatically by model)
        contract = Contract(
            created_by=user_id,
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
        await self.contract_repo.replace_search_tokens(contract.id, extracted.text)

        logger.info(
            "contract_uploaded",
            contract_id=str(contract.id),
            filename=filename,
            page_count=extracted.page_count,
        )

        return contract

    async def _check_quota(self, organization_id: UUID) -> None:
        """Ensure the organization has not exceeded its monthly contract limit."""
        limit = await self.contract_repo.get_contract_limit(organization_id)
        if limit is None:
            logger.warning(
                "quota_check_skipped_missing_org",
                organization_id=str(organization_id),
            )
            return
        if limit >= 999999:
            return

        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        used = await self.contract_repo.count_created_between(start, end, include_deleted=True)
        if used >= limit:
            raise QuotaExceededError("Vertragsanalysen", limit)

    async def perform_analysis(self, contract_id: UUID) -> ContractAnalysis:
        """Perform AI analysis on a contract.

        This is called by the background worker.

        Args:
            contract_id: ID of the contract to analyze

        Returns:
            ContractAnalysis with results
        """
        contract = await self._load_contract(contract_id)
        await self.contract_repo.update_status(contract, AnalysisStatus.PROCESSING)

        # Release the DB connection before long-running network I/O (AI call).
        await self.transaction.commit()

        start_time = time.monotonic()
        try:
            result, ai_response, prompt_version = await self._run_ai_analysis(contract, contract_id)
            analysis, findings = self._build_analysis(
                contract_id,
                result,
                ai_response,
                prompt_version,
                start_time,
            )
            await self._persist_analysis(contract, analysis, findings)

            logger.info(
                "contract_analysis_completed",
                contract_id=str(contract_id),
                risk_score=result.risk_score,
                findings_count=len(findings),
                processing_time_ms=analysis.processing_time_ms,
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

        # Release the DB connection before long-running network I/O (S3 delete).
        await self.transaction.commit()

        # Delete from S3
        await self.storage.delete(contract.file_path)

        # Soft delete record
        await self.contract_repo.soft_delete(contract)

        logger.info("contract_deleted", contract_id=str(contract_id))

    async def _extract_document(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
    ) -> ExtractedDocument:
        return await to_thread_limited(self.extractor.extract, content, filename, mime_type)

    async def _load_contract(self, contract_id: UUID) -> Contract:
        contract = await self.contract_repo.get_by_id(contract_id)
        if not contract:
            raise NotFoundError("Vertrag", str(contract_id))
        return contract

    async def _run_ai_analysis(
        self,
        contract: Contract,
        contract_id: UUID,
    ) -> tuple[ContractAnalysisResult, AIResponsePort, str]:
        prompt = ContractAnalysisPromptV1()
        contract_type_str = self._resolve_contract_type(contract)

        contract_text = contract.contract_text
        if contract_text is None:
            raise AnalysisFailedError(
                message="Contract text is missing; cannot run AI analysis",
                details={"contract_id": str(contract_id)},
            )

        ai_response = await self.ai_client.analyze_contract(
            contract_text=contract_text,
            contract_type=contract_type_str,
            resource_id=contract_id,
        )
        result = prompt.parse_response(ai_response.content)
        if result.contract_type_detected and not contract.contract_type:
            contract.contract_type = self._map_contract_type(result.contract_type_detected)
        return result, ai_response, prompt.version.version

    def _resolve_contract_type(self, contract: Contract) -> str | None:
        if not contract.contract_type:
            return None
        return (
            contract.contract_type.value
            if hasattr(contract.contract_type, "value")
            else contract.contract_type
        )

    def _build_analysis(
        self,
        contract_id: UUID,
        result: ContractAnalysisResult,
        ai_response: AIResponsePort,
        prompt_version: str,
        start_time: float,
    ) -> tuple[ContractAnalysis, list[ContractFinding]]:
        processing_time_ms = int((time.monotonic() - start_time) * 1000)
        analysis = ContractAnalysis(
            contract_id=contract_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            summary=result.summary,
            recommendations=result.recommendations,
            processing_time_ms=processing_time_ms,
            ai_model_version=ai_response.model,
            prompt_version=prompt_version,
            input_tokens=ai_response.input_tokens,
            output_tokens=ai_response.output_tokens,
            cost_cents=ai_response.cost_cents,
        )

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
        return analysis, findings

    async def _persist_analysis(
        self,
        contract: Contract,
        analysis: ContractAnalysis,
        findings: list[ContractFinding],
    ) -> None:
        async with self.contract_repo.begin_nested():
            await self.analysis_repo.create_with_findings(analysis, findings)
            await self.contract_repo.update_status(contract, AnalysisStatus.COMPLETED)

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
