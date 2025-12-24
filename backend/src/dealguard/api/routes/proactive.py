"""Proactive AI-Jurist API routes.

Endpoints for:
- Alerts management (list, view, actions)
- Deadlines (list, mark handled)
- Risk Radar (overview, history)
"""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.api.deps import get_db, get_current_user
from dealguard.infrastructure.database.models.user import User
from dealguard.infrastructure.database.models.proactive import (
    AlertStatus,
    AlertSeverity,
    AlertType,
    AlertSourceType,
    DeadlineStatus,
    DeadlineType,
)
from dealguard.domain.proactive import (
    DeadlineMonitoringService,
    AlertService,
    AlertFilter,
    RiskRadarService,
)

router = APIRouter(prefix="/proactive", tags=["Proactive AI-Jurist"])


# ─────────────────────────────────────────────────────────────
#                     SCHEMAS
# ─────────────────────────────────────────────────────────────


# Deadline schemas
class DeadlineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID
    contract_filename: str | None = None
    deadline_type: str
    deadline_date: date
    days_until: int
    is_overdue: bool
    needs_attention: bool
    reminder_days_before: int
    source_clause: str | None
    confidence: float
    is_verified: bool
    status: str
    notes: str | None


class DeadlineStatsResponse(BaseModel):
    total: int
    active: int
    overdue: int
    upcoming_7_days: int
    upcoming_30_days: int


class MarkDeadlineHandledRequest(BaseModel):
    action: str = Field(..., description="Action taken (e.g., 'terminated', 'renewed')")
    notes: str | None = None


class VerifyDeadlineRequest(BaseModel):
    correct_date: date | None = None


# Alert schemas
class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    source_id: UUID | None
    alert_type: str
    severity: str
    title: str
    description: str
    ai_recommendation: str | None
    recommended_actions: list[dict]
    related_contract_id: UUID | None
    related_contract_filename: str | None = None
    related_partner_id: UUID | None
    related_partner_name: str | None = None
    status: str
    snoozed_until: datetime | None
    due_date: date | None
    created_at: datetime


class AlertStatsResponse(BaseModel):
    total: int
    new: int
    seen: int
    in_progress: int
    resolved: int
    by_severity: dict[str, int]
    by_type: dict[str, int]


class ResolveAlertRequest(BaseModel):
    action: str = Field(..., description="Resolution action taken")
    notes: str | None = None


class SnoozeAlertRequest(BaseModel):
    days: int = Field(default=3, ge=1, le=30, description="Days to snooze")


class DismissAlertRequest(BaseModel):
    notes: str | None = None


# Risk Radar schemas
class RiskCategoryResponse(BaseModel):
    name: str
    score: int
    weight: float
    items_at_risk: int
    total_items: int
    trend: str
    key_issues: list[str]


class RiskRadarResponse(BaseModel):
    overall_score: int
    overall_trend: str
    categories: list[RiskCategoryResponse]
    urgent_alerts: int
    upcoming_deadlines: int
    recommendations: list[str]


class RiskSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    snapshot_date: date
    overall_risk_score: int
    contract_risk_score: int
    partner_risk_score: int
    compliance_score: int
    total_contracts: int
    high_risk_contracts: int
    total_partners: int
    high_risk_partners: int
    pending_deadlines: int
    open_alerts: int


# ─────────────────────────────────────────────────────────────
#                     HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────


def _deadline_to_response(d) -> DeadlineResponse:
    """Convert deadline model to response."""
    return DeadlineResponse(
        id=d.id,
        contract_id=d.contract_id,
        contract_filename=d.contract.filename if d.contract else None,
        deadline_type=d.deadline_type.value if isinstance(d.deadline_type, DeadlineType) else d.deadline_type,
        deadline_date=d.deadline_date,
        days_until=d.days_until,
        is_overdue=d.is_overdue,
        needs_attention=d.needs_attention,
        reminder_days_before=d.reminder_days_before,
        source_clause=d.source_clause,
        confidence=d.confidence,
        is_verified=d.is_verified,
        status=d.status.value if isinstance(d.status, DeadlineStatus) else d.status,
        notes=d.notes,
    )


def _alert_to_response(a) -> AlertResponse:
    """Convert alert model to response."""
    return AlertResponse(
        id=a.id,
        source_type=a.source_type.value if isinstance(a.source_type, AlertSourceType) else a.source_type,
        source_id=a.source_id,
        alert_type=a.alert_type.value if isinstance(a.alert_type, AlertType) else a.alert_type,
        severity=a.severity.value if isinstance(a.severity, AlertSeverity) else a.severity,
        title=a.title,
        description=a.description,
        ai_recommendation=a.ai_recommendation,
        recommended_actions=a.recommended_actions or [],
        related_contract_id=a.related_contract_id,
        related_contract_filename=a.related_contract.filename if a.related_contract else None,
        related_partner_id=a.related_partner_id,
        related_partner_name=a.related_partner.name if a.related_partner else None,
        status=a.status.value if isinstance(a.status, AlertStatus) else a.status,
        snoozed_until=a.snoozed_until,
        due_date=a.due_date,
        created_at=a.created_at,
    )


# ─────────────────────────────────────────────────────────────
#                     DEADLINES
# ─────────────────────────────────────────────────────────────


@router.get("/deadlines", response_model=list[DeadlineResponse])
async def list_deadlines(
    days_ahead: Annotated[int, Query(ge=1, le=365)] = 30,
    include_overdue: bool = True,
    contract_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List upcoming deadlines."""
    service = DeadlineMonitoringService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )

    if contract_id:
        deadlines = await service.get_deadlines_for_contract(contract_id)
    else:
        upcoming = await service.get_upcoming_deadlines(days_ahead=days_ahead)
        overdue = await service.get_overdue_deadlines() if include_overdue else []
        deadlines = list(overdue) + list(upcoming)

    return [_deadline_to_response(d) for d in deadlines]


@router.get("/deadlines/stats", response_model=DeadlineStatsResponse)
async def get_deadline_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get deadline statistics."""
    service = DeadlineMonitoringService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    stats = await service.get_deadline_stats()
    return DeadlineStatsResponse(
        total=stats.total,
        active=stats.active,
        overdue=stats.overdue,
        upcoming_7_days=stats.upcoming_7_days,
        upcoming_30_days=stats.upcoming_30_days,
    )


@router.post("/deadlines/{deadline_id}/handle", response_model=DeadlineResponse)
async def mark_deadline_handled(
    deadline_id: UUID,
    request: MarkDeadlineHandledRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a deadline as handled."""
    service = DeadlineMonitoringService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    deadline = await service.mark_deadline_handled(
        deadline_id=deadline_id,
        action=request.action,
        notes=request.notes,
    )

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    await db.commit()
    return _deadline_to_response(deadline)


@router.post("/deadlines/{deadline_id}/dismiss", response_model=DeadlineResponse)
async def dismiss_deadline(
    deadline_id: UUID,
    request: DismissAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a deadline (mark as not relevant)."""
    service = DeadlineMonitoringService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    deadline = await service.dismiss_deadline(
        deadline_id=deadline_id,
        notes=request.notes,
    )

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    await db.commit()
    return _deadline_to_response(deadline)


@router.post("/deadlines/{deadline_id}/verify", response_model=DeadlineResponse)
async def verify_deadline(
    deadline_id: UUID,
    request: VerifyDeadlineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify an AI-extracted deadline (human confirmation)."""
    service = DeadlineMonitoringService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    deadline = await service.verify_deadline(
        deadline_id=deadline_id,
        correct_date=request.correct_date,
    )

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    await db.commit()
    return _deadline_to_response(deadline)


# ─────────────────────────────────────────────────────────────
#                     ALERTS
# ─────────────────────────────────────────────────────────────


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    status_filter: Annotated[list[str] | None, Query(alias="status")] = None,
    severity_filter: Annotated[list[str] | None, Query(alias="severity")] = None,
    include_snoozed: bool = False,
    contract_id: UUID | None = None,
    partner_id: UUID | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List proactive alerts with filtering."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )

    # Build filter
    filter_obj = AlertFilter(
        status=[AlertStatus(s) for s in status_filter] if status_filter else None,
        severity=[AlertSeverity(s) for s in severity_filter] if severity_filter else None,
        contract_id=contract_id,
        partner_id=partner_id,
        include_snoozed=include_snoozed,
    )

    alerts = await service.list_alerts(filter=filter_obj, offset=offset, limit=limit)
    return [_alert_to_response(a) for a in alerts]


@router.get("/alerts/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alert statistics."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    stats = await service.get_stats()
    return AlertStatsResponse(
        total=stats.total,
        new=stats.new,
        seen=stats.seen,
        in_progress=stats.in_progress,
        resolved=stats.resolved,
        by_severity=stats.by_severity,
        by_type=stats.by_type,
    )


@router.get("/alerts/count", response_model=dict)
async def get_new_alert_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of new alerts (for badge display)."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    count = await service.count_new_alerts()
    return {"count": count}


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single alert by ID."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    alert = await service.get_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Mark as seen when viewed
    await service.mark_seen(alert_id)
    await db.commit()
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    request: ResolveAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve an alert (action taken)."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    alert = await service.resolve(
        alert_id=alert_id,
        action=request.action,
        notes=request.notes,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(
    alert_id: UUID,
    request: DismissAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss an alert (not relevant)."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    alert = await service.dismiss(
        alert_id=alert_id,
        notes=request.notes,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()
    return _alert_to_response(alert)


@router.post("/alerts/{alert_id}/snooze", response_model=AlertResponse)
async def snooze_alert(
    alert_id: UUID,
    request: SnoozeAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Snooze an alert for a specified number of days."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    alert = await service.snooze(
        alert_id=alert_id,
        days=request.days,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()
    return _alert_to_response(alert)


@router.post("/alerts/mark-all-seen", response_model=dict)
async def mark_all_alerts_seen(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all new alerts as seen."""
    service = AlertService(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    count = await service.mark_all_seen()
    await db.commit()
    return {"marked_seen": count}


# ─────────────────────────────────────────────────────────────
#                     RISK RADAR
# ─────────────────────────────────────────────────────────────


@router.get("/risk-radar", response_model=RiskRadarResponse)
async def get_risk_radar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current risk radar overview."""
    service = RiskRadarService(db, organization_id=current_user.organization_id)
    radar = await service.get_risk_radar()

    return RiskRadarResponse(
        overall_score=radar.overall_score,
        overall_trend=radar.overall_trend,
        categories=[
            RiskCategoryResponse(
                name=cat.name,
                score=cat.score,
                weight=cat.weight,
                items_at_risk=cat.items_at_risk,
                total_items=cat.total_items,
                trend=cat.trend,
                key_issues=cat.key_issues,
            )
            for cat in radar.categories
        ],
        urgent_alerts=radar.urgent_alerts,
        upcoming_deadlines=radar.upcoming_deadlines,
        recommendations=radar.recommendations,
    )


@router.get("/risk-radar/history", response_model=list[RiskSnapshotResponse])
async def get_risk_history(
    days: Annotated[int, Query(ge=7, le=365)] = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get risk history for trending chart."""
    service = RiskRadarService(db, organization_id=current_user.organization_id)
    snapshots = await service.get_risk_history(days=days)

    return [
        RiskSnapshotResponse(
            id=s.id,
            snapshot_date=s.snapshot_date,
            overall_risk_score=s.overall_risk_score,
            contract_risk_score=s.contract_risk_score,
            partner_risk_score=s.partner_risk_score,
            compliance_score=s.compliance_score,
            total_contracts=s.total_contracts,
            high_risk_contracts=s.high_risk_contracts,
            total_partners=s.total_partners,
            high_risk_partners=s.high_risk_partners,
            pending_deadlines=s.pending_deadlines,
            open_alerts=s.open_alerts,
        )
        for s in snapshots
    ]
