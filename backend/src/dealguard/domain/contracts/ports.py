"""Ports for contract analysis dependencies."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import AsyncContextManager, Protocol
from uuid import UUID

from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
    ContractAnalysis,
    ContractFinding,
    ContractType,
)


class ExtractedDocument(Protocol):
    """Minimal extracted document contract for analysis flow."""

    text: str
    page_count: int
    file_hash: str
    file_size_bytes: int


class DocumentExtractorPort(Protocol):
    """Document extraction interface."""

    def extract(self, content: bytes, filename: str, mime_type: str) -> ExtractedDocument:
        """Extract text and metadata from a document."""


class AIResponsePort(Protocol):
    """AI response interface needed by analysis pipeline."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_cents: float


class AIClientPort(Protocol):
    """AI client interface for contract analysis."""

    async def analyze_contract(
        self,
        contract_text: str,
        contract_type: str | None,
        resource_id: UUID | None = None,
    ) -> AIResponsePort:
        """Analyze contract text and return an AI response."""


class StoragePort(Protocol):
    """Storage interface for contract files."""

    async def upload(
        self,
        content: bytes,
        organization_id: UUID,
        filename: str,
        mime_type: str,
    ) -> tuple[str, UUID]:
        """Upload a contract file and return the storage key and document ID."""

    async def delete(self, key: str) -> None:
        """Delete a stored object."""


class ContractRepositoryPort(Protocol):
    """Repository interface for contracts."""

    async def get_by_id(self, id: UUID) -> Contract | None:
        """Get contract by ID."""

    async def get_by_id_with_analysis(self, id: UUID) -> Contract | None:
        """Get contract with analysis and findings."""

    async def get_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[Contract]:
        """List contracts for the current tenant."""

    async def get_by_file_hash(self, file_hash: str) -> Contract | None:
        """Find contract by file hash."""

    async def create(self, entity: Contract) -> Contract:
        """Persist a contract."""

    async def update_status(
        self,
        contract: Contract,
        status: AnalysisStatus,
        error_message: str | None = None,
    ) -> Contract:
        """Update contract status."""

    async def count_created_between(
        self,
        start: datetime,
        end: datetime,
        *,
        include_deleted: bool = False,
    ) -> int:
        """Count contracts created in a time window."""

    async def soft_delete(self, entity: Contract) -> Contract:
        """Soft-delete a contract."""

    async def get_contract_limit(self, organization_id: UUID) -> int | None:
        """Get the contract limit for an organization."""

    def begin_nested(self) -> AsyncContextManager[None]:
        """Create a nested transaction context."""


class ContractAnalysisRepositoryPort(Protocol):
    """Repository interface for contract analyses."""

    async def create_with_findings(
        self,
        analysis: ContractAnalysis,
        findings: list[ContractFinding],
    ) -> ContractAnalysis:
        """Persist analysis with findings."""
