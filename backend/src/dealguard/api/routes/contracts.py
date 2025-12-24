"""Contract API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from dealguard.api.middleware.auth import CurrentUser, RequireMember
from dealguard.api.ratelimit import limiter, RATE_LIMIT_UPLOAD, RATE_LIMIT_DEFAULT
from dealguard.domain.contracts.services import ContractAnalysisService
from dealguard.infrastructure.ai.cost_tracker import CostTracker
from dealguard.infrastructure.ai.factory import get_ai_client
from dealguard.infrastructure.database.connection import SessionDep
from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    ContractType,
    FindingCategory,
    FindingSeverity,
    RiskLevel,
)
from dealguard.infrastructure.database.repositories.contract import (
    ContractAnalysisRepository,
    ContractRepository,
)
from dealguard.infrastructure.document.extractor import DocumentExtractor
from dealguard.infrastructure.queue.client import enqueue_contract_analysis
from dealguard.infrastructure.storage.s3 import S3Storage
from dealguard.shared.exceptions import NotFoundError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# ----- Response Schemas -----


class ContractFindingResponse(BaseModel):
    """Finding response schema."""

    id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    original_clause_text: str | None
    clause_location: dict | None
    suggested_change: str | None
    market_comparison: str | None


class ContractAnalysisResponse(BaseModel):
    """Analysis response schema."""

    id: str
    risk_score: int
    risk_level: RiskLevel
    summary: str
    recommendations: list[str]
    findings: list[ContractFindingResponse]
    processing_time_ms: int
    created_at: str


class ContractResponse(BaseModel):
    """Contract response schema."""

    id: str
    filename: str
    file_size_bytes: int
    page_count: int | None
    contract_type: ContractType | None
    status: AnalysisStatus
    created_at: str
    analysis: ContractAnalysisResponse | None = None


class ContractListResponse(BaseModel):
    """Paginated contract list."""

    items: list[ContractResponse]
    total: int
    limit: int
    offset: int


class UploadResponse(BaseModel):
    """Upload response."""

    id: str
    filename: str
    status: AnalysisStatus
    message: str


# ----- Dependencies -----


async def get_contract_service(session: SessionDep) -> ContractAnalysisService:
    """Get contract analysis service."""
    return ContractAnalysisService(
        contract_repo=ContractRepository(session),
        analysis_repo=ContractAnalysisRepository(session),
        ai_client=get_ai_client(CostTracker()),
        storage=S3Storage(),
        extractor=DocumentExtractor(),
    )


ContractServiceDep = Annotated[ContractAnalysisService, Depends(get_contract_service)]


# ----- Routes -----


@router.post("/", response_model=UploadResponse, status_code=202)
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_contract(
    request: Request,
    user: RequireMember,
    service: ContractServiceDep,
    file: UploadFile = File(...),
    contract_type: ContractType | None = Form(None),
) -> UploadResponse:
    """Upload a contract for analysis.

    The contract will be queued for processing. Use GET /contracts/{id}
    to poll for results.

    Supported formats: PDF, DOCX
    Max file size: 50 MB
    """
    if not file.content_type:
        raise HTTPException(400, "Dateityp nicht erkannt")

    content = await file.read()

    contract = await service.upload_contract(
        content=content,
        filename=file.filename or "unknown",
        mime_type=file.content_type,
        contract_type=contract_type,
        organization_id=user.organization_id,
        user_id=user.id,
    )

    # Queue background analysis job
    job_id = await enqueue_contract_analysis(
        contract_id=contract.id,
        organization_id=user.organization_id,
        user_id=user.id,
    )

    if job_id:
        logger.info(
            "contract_analysis_queued",
            contract_id=str(contract.id),
            job_id=job_id,
        )
    else:
        logger.warning(
            "contract_analysis_queue_failed",
            contract_id=str(contract.id),
        )

    return UploadResponse(
        id=str(contract.id),
        filename=contract.filename,
        status=contract.status,
        message="Vertrag wird analysiert. Bitte Status abfragen.",
    )


@router.get("/", response_model=ContractListResponse)
async def list_contracts(
    user: CurrentUser,
    service: ContractServiceDep,
    limit: int = 20,
    offset: int = 0,
) -> ContractListResponse:
    """List all contracts for the current organization."""
    contracts = await service.list_contracts(limit=limit, offset=offset)
    total = await service.contract_repo.count()

    items = [
        ContractResponse(
            id=str(c.id),
            filename=c.filename,
            file_size_bytes=c.file_size_bytes,
            page_count=c.page_count,
            contract_type=c.contract_type,
            status=c.status,
            created_at=c.created_at.isoformat(),
        )
        for c in contracts
    ]

    return ContractListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: UUID,
    user: CurrentUser,
    service: ContractServiceDep,
) -> ContractResponse:
    """Get contract details with analysis results."""
    contract = await service.get_contract(contract_id)

    if not contract:
        raise HTTPException(404, "Vertrag nicht gefunden")

    # Build analysis response if available
    analysis_response = None
    if contract.analysis:
        a = contract.analysis
        findings = [
            ContractFindingResponse(
                id=str(f.id),
                category=f.category,
                severity=f.severity,
                title=f.title,
                description=f.description,
                original_clause_text=f.original_clause_text,
                clause_location=f.clause_location,
                suggested_change=f.suggested_change,
                market_comparison=f.market_comparison,
            )
            for f in a.findings
        ]

        analysis_response = ContractAnalysisResponse(
            id=str(a.id),
            risk_score=a.risk_score,
            risk_level=a.risk_level,
            summary=a.summary,
            recommendations=a.recommendations,
            findings=findings,
            processing_time_ms=a.processing_time_ms,
            created_at=a.created_at.isoformat(),
        )

    return ContractResponse(
        id=str(contract.id),
        filename=contract.filename,
        file_size_bytes=contract.file_size_bytes,
        page_count=contract.page_count,
        contract_type=contract.contract_type,
        status=contract.status,
        created_at=contract.created_at.isoformat(),
        analysis=analysis_response,
    )


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: UUID,
    user: RequireMember,
    service: ContractServiceDep,
) -> None:
    """Delete a contract."""
    try:
        await service.delete_contract(contract_id)
    except NotFoundError:
        raise HTTPException(404, "Vertrag nicht gefunden")


@router.post("/{contract_id}/analyze", response_model=ContractResponse)
async def trigger_analysis(
    contract_id: UUID,
    user: RequireMember,
    service: ContractServiceDep,
) -> ContractResponse:
    """Manually trigger analysis for a contract.

    This is mainly for testing/development. In production,
    analysis is triggered automatically on upload.
    """
    contract = await service.get_contract(contract_id)
    if not contract:
        raise HTTPException(404, "Vertrag nicht gefunden")

    if contract.status not in (AnalysisStatus.PENDING, AnalysisStatus.FAILED):
        raise HTTPException(400, "Vertrag wird bereits analysiert oder ist fertig")

    # Run analysis synchronously for now
    await service.perform_analysis(contract_id)

    # Refresh and return
    contract = await service.get_contract(contract_id)
    return await get_contract(contract_id, user, service)
