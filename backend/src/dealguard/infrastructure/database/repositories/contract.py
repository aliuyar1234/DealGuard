"""Contract repository."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import selectinload

from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
    ContractAnalysis,
    ContractFinding,
)
from dealguard.infrastructure.database.models.contract_search import ContractSearchToken
from dealguard.infrastructure.database.models.organization import Organization
from dealguard.infrastructure.database.repositories.base import BaseRepository
from dealguard.shared.search_tokens import token_hashes_from_text


class ContractRepository(BaseRepository[Contract]):
    """Repository for Contract entities."""

    model_class = Contract

    async def get_by_id_with_analysis(self, id: UUID) -> Contract | None:
        """Get contract with its analysis and findings eagerly loaded."""
        query = (
            self._base_query()
            .where(Contract.id == id)
            .options(selectinload(Contract.analysis).selectinload(ContractAnalysis.findings))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_file_hash(self, file_hash: str) -> Contract | None:
        """Get contract by file hash (for deduplication)."""
        query = self._base_query().where(Contract.file_hash == file_hash)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def replace_search_tokens(self, contract_id: UUID, contract_text: str) -> None:
        """Replace the search token index for a contract."""
        org_id = self._get_organization_id()

        await self.session.execute(
            delete(ContractSearchToken).where(
                ContractSearchToken.organization_id == org_id,
                ContractSearchToken.contract_id == contract_id,
            )
        )

        token_hashes = token_hashes_from_text(contract_text)
        if not token_hashes:
            return

        await self.session.execute(
            insert(ContractSearchToken),
            [
                {
                    "organization_id": org_id,
                    "token_hash": token_hash,
                    "contract_id": contract_id,
                }
                for token_hash in token_hashes
            ],
        )

    async def get_pending(self, limit: int = 10) -> Sequence[Contract]:
        """Get pending contracts for processing."""
        query = (
            self._base_query()
            .where(Contract.status == AnalysisStatus.PENDING)
            .order_by(Contract.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_status(
        self,
        status: AnalysisStatus,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Contract]:
        """Get contracts by status."""
        query = (
            self._base_query()
            .where(Contract.status == status)
            .order_by(Contract.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_created_between(
        self,
        start: datetime,
        end: datetime,
        *,
        include_deleted: bool = False,
    ) -> int:
        """Count contracts created between two timestamps for the current tenant."""
        query = self._base_query(include_deleted=include_deleted).where(
            Contract.created_at >= start,
            Contract.created_at < end,
        )
        result = await self.session.execute(select(func.count()).select_from(query.subquery()))
        return result.scalar_one()

    async def update_status(
        self,
        contract: Contract,
        status: AnalysisStatus,
        error_message: str | None = None,
    ) -> Contract:
        """Update contract status."""
        contract.status = status
        contract.error_message = error_message
        return await self.update(contract)

    async def get_contract_limit(self, organization_id: UUID) -> int | None:
        """Fetch contract limit for an organization."""
        organization = await self.session.get(Organization, organization_id)
        if not organization:
            return None
        return organization.contract_limit


class ContractAnalysisRepository(BaseRepository[ContractAnalysis]):
    """Repository for ContractAnalysis entities."""

    model_class = ContractAnalysis

    async def get_by_contract_id(self, contract_id: UUID) -> ContractAnalysis | None:
        """Get analysis by contract ID."""
        query = (
            self._base_query()
            .where(ContractAnalysis.contract_id == contract_id)
            .options(selectinload(ContractAnalysis.findings))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_with_findings(
        self,
        analysis: ContractAnalysis,
        findings: list[ContractFinding],
    ) -> ContractAnalysis:
        """Create analysis with its findings."""
        # Set organization_id for all
        org_id = self._get_organization_id()
        analysis.organization_id = org_id

        # First save the analysis to get its ID
        self.session.add(analysis)
        await self.session.flush()

        # Now we have analysis.id, add findings
        for finding in findings:
            finding.organization_id = org_id
            finding.analysis_id = analysis.id
            self.session.add(finding)

        await self.session.flush()
        await self.session.refresh(analysis)
        return analysis
