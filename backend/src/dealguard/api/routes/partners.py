"""Partner API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dealguard.api.middleware.auth import CurrentUser, RequireMember
from dealguard.domain.partners.services import PartnerService
from dealguard.domain.partners.check_service import PartnerCheckService
from dealguard.infrastructure.database.connection import SessionDep
from dealguard.infrastructure.external.mock_provider import (
    MockCompanyProvider,
    MockCreditProvider,
    MockSanctionProvider,
    MockInsolvencyProvider,
)
from dealguard.infrastructure.database.models.partner import (
    PartnerType,
    PartnerRiskLevel,
    CheckType,
    CheckStatus,
    AlertSeverity,
    AlertType,
)
from dealguard.infrastructure.database.repositories.partner import (
    PartnerRepository,
    PartnerCheckRepository,
    PartnerAlertRepository,
    ContractPartnerRepository,
)
from dealguard.shared.exceptions import NotFoundError, ValidationError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/partners", tags=["Partners"])


# ----- Request/Response Schemas -----


class PartnerCreateRequest(BaseModel):
    """Create partner request."""

    name: str = Field(..., min_length=1, max_length=255)
    partner_type: PartnerType = PartnerType.OTHER
    handelsregister_id: str | None = None
    tax_id: str | None = None
    vat_id: str | None = None
    street: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str = "DE"
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class PartnerUpdateRequest(BaseModel):
    """Update partner request."""

    name: str | None = None
    partner_type: PartnerType | None = None
    handelsregister_id: str | None = None
    tax_id: str | None = None
    vat_id: str | None = None
    street: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_watched: bool | None = None


class PartnerCheckResponse(BaseModel):
    """Partner check response."""

    id: str
    check_type: CheckType
    status: CheckStatus
    score: int | None
    result_summary: str | None
    provider: str | None
    created_at: str


class PartnerAlertResponse(BaseModel):
    """Partner alert response."""

    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    source: str | None
    source_url: str | None
    is_read: bool
    is_dismissed: bool
    created_at: str


class ContractLinkResponse(BaseModel):
    """Contract link response."""

    id: str
    contract_id: str
    contract_filename: str | None = None
    role: str | None
    notes: str | None
    created_at: str


class PartnerResponse(BaseModel):
    """Partner response schema."""

    id: str
    name: str
    partner_type: PartnerType
    handelsregister_id: str | None
    tax_id: str | None
    vat_id: str | None
    street: str | None
    city: str | None
    postal_code: str | None
    country: str
    website: str | None
    email: str | None
    phone: str | None
    notes: str | None
    risk_score: int | None
    risk_level: PartnerRiskLevel
    last_check_at: str | None
    is_watched: bool
    created_at: str
    # Optional details
    checks: list[PartnerCheckResponse] | None = None
    alerts: list[PartnerAlertResponse] | None = None
    contracts: list[ContractLinkResponse] | None = None


class PartnerListResponse(BaseModel):
    """Paginated partner list."""

    items: list[PartnerResponse]
    total: int
    limit: int
    offset: int


class LinkContractRequest(BaseModel):
    """Link contract to partner request."""

    contract_id: str
    role: str | None = None
    notes: str | None = None


class AlertCountResponse(BaseModel):
    """Alert count response."""

    unread_count: int


# ----- Dependencies -----


async def get_partner_service(session: SessionDep) -> PartnerService:
    """Get partner service."""
    return PartnerService(
        partner_repo=PartnerRepository(session),
        check_repo=PartnerCheckRepository(session),
        alert_repo=PartnerAlertRepository(session),
        contract_partner_repo=ContractPartnerRepository(session),
    )


PartnerServiceDep = Annotated[PartnerService, Depends(get_partner_service)]


async def get_partner_check_service(session: SessionDep) -> PartnerCheckService:
    """Get partner check service with mock providers for development."""
    return PartnerCheckService(
        partner_repo=PartnerRepository(session),
        check_repo=PartnerCheckRepository(session),
        company_provider=MockCompanyProvider(),
        credit_provider=MockCreditProvider(),
        sanction_provider=MockSanctionProvider(),
        insolvency_provider=MockInsolvencyProvider(),
    )


PartnerCheckServiceDep = Annotated[PartnerCheckService, Depends(get_partner_check_service)]


# ----- Helper Functions -----


def _partner_to_response(partner, include_details: bool = False) -> PartnerResponse:
    """Convert Partner model to response."""
    response = PartnerResponse(
        id=str(partner.id),
        name=partner.name,
        partner_type=partner.partner_type,
        handelsregister_id=partner.handelsregister_id,
        tax_id=partner.tax_id,
        vat_id=partner.vat_id,
        street=partner.street,
        city=partner.city,
        postal_code=partner.postal_code,
        country=partner.country,
        website=partner.website,
        email=partner.email,
        phone=partner.phone,
        notes=partner.notes,
        risk_score=partner.risk_score,
        risk_level=partner.risk_level,
        last_check_at=partner.last_check_at.isoformat() if partner.last_check_at else None,
        is_watched=partner.is_watched,
        created_at=partner.created_at.isoformat(),
    )

    if include_details:
        # Add checks
        if hasattr(partner, 'checks') and partner.checks:
            response.checks = [
                PartnerCheckResponse(
                    id=str(c.id),
                    check_type=c.check_type,
                    status=c.status,
                    score=c.score,
                    result_summary=c.result_summary,
                    provider=c.provider,
                    created_at=c.created_at.isoformat(),
                )
                for c in partner.checks[:10]  # Limit to 10
            ]

        # Add alerts
        if hasattr(partner, 'alerts') and partner.alerts:
            response.alerts = [
                PartnerAlertResponse(
                    id=str(a.id),
                    alert_type=a.alert_type,
                    severity=a.severity,
                    title=a.title,
                    description=a.description,
                    source=a.source,
                    source_url=a.source_url,
                    is_read=a.is_read,
                    is_dismissed=a.is_dismissed,
                    created_at=a.created_at.isoformat(),
                )
                for a in partner.alerts[:10]  # Limit to 10
            ]

        # Add contract links
        if hasattr(partner, 'contract_links') and partner.contract_links:
            response.contracts = [
                ContractLinkResponse(
                    id=str(cl.id),
                    contract_id=str(cl.contract_id),
                    contract_filename=cl.contract.filename if cl.contract else None,
                    role=cl.role,
                    notes=cl.notes,
                    created_at=cl.created_at.isoformat(),
                )
                for cl in partner.contract_links
            ]

    return response


# ----- Routes -----


@router.post("/", response_model=PartnerResponse, status_code=201)
async def create_partner(
    user: RequireMember,
    service: PartnerServiceDep,
    request: PartnerCreateRequest,
) -> PartnerResponse:
    """Create a new partner."""
    partner = await service.create_partner(
        name=request.name,
        partner_type=request.partner_type,
        handelsregister_id=request.handelsregister_id,
        tax_id=request.tax_id,
        vat_id=request.vat_id,
        street=request.street,
        city=request.city,
        postal_code=request.postal_code,
        country=request.country,
        website=request.website,
        email=request.email,
        phone=request.phone,
        notes=request.notes,
    )
    return _partner_to_response(partner)


@router.get("/", response_model=PartnerListResponse)
async def list_partners(
    user: CurrentUser,
    service: PartnerServiceDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PartnerListResponse:
    """List all partners for the current organization."""
    partners = await service.list_partners(limit=limit, offset=offset)
    total = await service.partner_repo.count()

    return PartnerListResponse(
        items=[_partner_to_response(p) for p in partners],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=list[PartnerResponse])
async def search_partners(
    user: CurrentUser,
    service: PartnerServiceDep,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
) -> list[PartnerResponse]:
    """Search partners by name or identifiers."""
    partners = await service.search_partners(q, limit=limit)
    return [_partner_to_response(p) for p in partners]


@router.get("/high-risk", response_model=list[PartnerResponse])
async def get_high_risk_partners(
    user: CurrentUser,
    service: PartnerServiceDep,
) -> list[PartnerResponse]:
    """Get all high-risk partners."""
    partners = await service.get_high_risk_partners()
    return [_partner_to_response(p) for p in partners]


@router.get("/watched", response_model=list[PartnerResponse])
async def get_watched_partners(
    user: CurrentUser,
    service: PartnerServiceDep,
) -> list[PartnerResponse]:
    """Get all watched partners."""
    partners = await service.get_watched_partners()
    return [_partner_to_response(p) for p in partners]


@router.get("/alerts/count", response_model=AlertCountResponse)
async def get_alert_count(
    user: CurrentUser,
    service: PartnerServiceDep,
) -> AlertCountResponse:
    """Get count of unread alerts."""
    count = await service.get_unread_alert_count()
    return AlertCountResponse(unread_count=count)


@router.get("/alerts", response_model=list[PartnerAlertResponse])
async def get_all_alerts(
    user: CurrentUser,
    service: PartnerServiceDep,
) -> list[PartnerAlertResponse]:
    """Get all unread alerts for the organization."""
    alerts = await service.get_all_unread_alerts()
    return [
        PartnerAlertResponse(
            id=str(a.id),
            alert_type=a.alert_type,
            severity=a.severity,
            title=a.title,
            description=a.description,
            source=a.source,
            source_url=a.source_url,
            is_read=a.is_read,
            is_dismissed=a.is_dismissed,
            created_at=a.created_at.isoformat(),
        )
        for a in alerts
    ]


@router.get("/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    partner_id: UUID,
    user: CurrentUser,
    service: PartnerServiceDep,
) -> PartnerResponse:
    """Get partner details with checks, alerts, and contracts."""
    partner = await service.get_partner(partner_id)
    if not partner:
        raise HTTPException(404, "Partner nicht gefunden")
    return _partner_to_response(partner, include_details=True)


@router.patch("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: UUID,
    user: RequireMember,
    service: PartnerServiceDep,
    request: PartnerUpdateRequest,
) -> PartnerResponse:
    """Update partner details."""
    try:
        partner = await service.update_partner(
            partner_id,
            name=request.name,
            partner_type=request.partner_type,
            handelsregister_id=request.handelsregister_id,
            tax_id=request.tax_id,
            vat_id=request.vat_id,
            street=request.street,
            city=request.city,
            postal_code=request.postal_code,
            country=request.country,
            website=request.website,
            email=request.email,
            phone=request.phone,
            notes=request.notes,
            is_watched=request.is_watched,
        )
        return _partner_to_response(partner)
    except NotFoundError:
        raise HTTPException(404, "Partner nicht gefunden")


@router.delete("/{partner_id}", status_code=204)
async def delete_partner(
    partner_id: UUID,
    user: RequireMember,
    service: PartnerServiceDep,
) -> None:
    """Delete a partner."""
    try:
        await service.delete_partner(partner_id)
    except NotFoundError:
        raise HTTPException(404, "Partner nicht gefunden")


@router.post("/{partner_id}/contracts", response_model=ContractLinkResponse, status_code=201)
async def link_contract(
    partner_id: UUID,
    user: RequireMember,
    service: PartnerServiceDep,
    request: LinkContractRequest,
) -> ContractLinkResponse:
    """Link a contract to this partner."""
    try:
        link = await service.link_to_contract(
            partner_id=partner_id,
            contract_id=UUID(request.contract_id),
            role=request.role,
            notes=request.notes,
        )
        return ContractLinkResponse(
            id=str(link.id),
            contract_id=str(link.contract_id),
            role=link.role,
            notes=link.notes,
            created_at=link.created_at.isoformat(),
        )
    except NotFoundError:
        raise HTTPException(404, "Partner nicht gefunden")
    except ValidationError as e:
        raise HTTPException(400, str(e))


@router.delete("/{partner_id}/contracts/{contract_id}", status_code=204)
async def unlink_contract(
    partner_id: UUID,
    contract_id: UUID,
    user: RequireMember,
    service: PartnerServiceDep,
) -> None:
    """Unlink a contract from this partner."""
    removed = await service.unlink_from_contract(partner_id, contract_id)
    if not removed:
        raise HTTPException(404, "Verknüpfung nicht gefunden")


@router.post("/{partner_id}/recalculate-risk", response_model=PartnerResponse)
async def recalculate_risk(
    partner_id: UUID,
    user: RequireMember,
    service: PartnerServiceDep,
) -> PartnerResponse:
    """Recalculate partner's risk score from available checks."""
    try:
        partner = await service.calculate_risk_score(partner_id)
        return _partner_to_response(partner)
    except NotFoundError:
        raise HTTPException(404, "Partner nicht gefunden")


@router.post("/{partner_id}/run-checks", response_model=list[PartnerCheckResponse])
async def run_all_checks(
    partner_id: UUID,
    user: RequireMember,
    check_service: PartnerCheckServiceDep,
    service: PartnerServiceDep,
) -> list[PartnerCheckResponse]:
    """Run all available external checks for a partner.

    This will query external APIs for company data, credit info, sanctions, etc.
    In development mode, mock providers are used.
    """
    try:
        checks = await check_service.run_all_checks(partner_id)

        # Recalculate risk after checks
        await service.calculate_risk_score(partner_id)

        return [
            PartnerCheckResponse(
                id=str(c.id),
                check_type=c.check_type,
                status=c.status,
                score=c.score,
                result_summary=c.result_summary,
                provider=c.provider,
                created_at=c.created_at.isoformat(),
            )
            for c in checks
        ]
    except NotFoundError:
        raise HTTPException(404, "Partner nicht gefunden")


@router.post("/alerts/{alert_id}/read", response_model=PartnerAlertResponse)
async def mark_alert_read(
    alert_id: UUID,
    user: CurrentUser,
    service: PartnerServiceDep,
) -> PartnerAlertResponse:
    """Mark an alert as read."""
    try:
        alert = await service.mark_alert_read(alert_id)
        return PartnerAlertResponse(
            id=str(alert.id),
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            source=alert.source,
            source_url=alert.source_url,
            is_read=alert.is_read,
            is_dismissed=alert.is_dismissed,
            created_at=alert.created_at.isoformat(),
        )
    except NotFoundError:
        raise HTTPException(404, "Alert nicht gefunden")


@router.post("/alerts/{alert_id}/dismiss", response_model=PartnerAlertResponse)
async def dismiss_alert(
    alert_id: UUID,
    user: CurrentUser,
    service: PartnerServiceDep,
) -> PartnerAlertResponse:
    """Dismiss an alert."""
    try:
        alert = await service.dismiss_alert(alert_id)
        return PartnerAlertResponse(
            id=str(alert.id),
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            source=alert.source,
            source_url=alert.source_url,
            is_read=alert.is_read,
            is_dismissed=alert.is_dismissed,
            created_at=alert.created_at.isoformat(),
        )
    except NotFoundError:
        raise HTTPException(404, "Alert nicht gefunden")
