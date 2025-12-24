"""Risk Radar service - Combined risk monitoring.

This service provides:
1. Unified risk view across contracts, partners, compliance
2. Daily risk snapshots for trending
3. Risk change detection and alerting
4. Organization-wide risk score calculation
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.infrastructure.database.models.contract import Contract, ContractAnalysis
from dealguard.infrastructure.database.models.partner import Partner, PartnerRiskLevel
from dealguard.infrastructure.database.models.proactive import (
    AlertSeverity,
    AlertStatus,
    ComplianceCheck,
    ComplianceStatus,
    ContractDeadline,
    DeadlineStatus,
    ProactiveAlert,
    RiskSnapshot,
)
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskCategory:
    """Risk score for a single category."""

    name: str
    score: int  # 0-100 (0 = no risk, 100 = critical)
    weight: float  # How much this contributes to overall score
    items_at_risk: int
    total_items: int
    trend: str  # "improving", "stable", "worsening"
    key_issues: list[str]


@dataclass
class RiskRadarResult:
    """Complete risk radar assessment."""

    overall_score: int  # 0-100
    overall_trend: str  # "improving", "stable", "worsening"
    categories: list[RiskCategory]
    urgent_alerts: int
    upcoming_deadlines: int
    recommendations: list[str]


class RiskRadarService:
    """Service for unified risk monitoring.

    Combines:
    - Contract risk (from AI analysis)
    - Partner risk (from checks)
    - Compliance risk (from compliance checks)
    - Deadline risk (upcoming/overdue)

    Produces:
    - Real-time risk radar
    - Daily snapshots for trending
    - Change alerts
    """

    # Category weights (must sum to 1.0)
    WEIGHTS = {
        "contracts": 0.30,
        "partners": 0.25,
        "compliance": 0.25,
        "deadlines": 0.20,
    }

    def __init__(self, session: AsyncSession, *, organization_id: UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def _get_organization_id(self) -> UUID:
        return self.organization_id

    # ─────────────────────────────────────────────────────────────
    #                  RISK RADAR (REAL-TIME)
    # ─────────────────────────────────────────────────────────────

    async def get_risk_radar(self) -> RiskRadarResult:
        """Calculate current risk radar for the organization."""
        # Get all category scores
        contract_risk = await self._calculate_contract_risk()
        partner_risk = await self._calculate_partner_risk()
        compliance_risk = await self._calculate_compliance_risk()
        deadline_risk = await self._calculate_deadline_risk()

        categories = [contract_risk, partner_risk, compliance_risk, deadline_risk]

        # Calculate overall score
        overall_score = int(sum(cat.score * cat.weight for cat in categories))

        # Determine trend by comparing to yesterday's snapshot
        overall_trend = await self._determine_overall_trend(overall_score)

        # Count urgent items
        urgent_alerts = await self._count_urgent_alerts()
        upcoming_deadlines = await self._count_upcoming_deadlines()

        # Generate recommendations
        recommendations = self._generate_recommendations(categories)

        return RiskRadarResult(
            overall_score=overall_score,
            overall_trend=overall_trend,
            categories=categories,
            urgent_alerts=urgent_alerts,
            upcoming_deadlines=upcoming_deadlines,
            recommendations=recommendations,
        )

    async def _calculate_contract_risk(self) -> RiskCategory:
        """Calculate contract risk score.

        Avoids loading all contracts/analyses into memory by using aggregates.
        """
        org_id = self._get_organization_id()

        total_query = (
            select(func.count())
            .select_from(Contract)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return RiskCategory(
                name="Verträge",
                score=0,
                weight=self.WEIGHTS["contracts"],
                items_at_risk=0,
                total_items=0,
                trend="stable",
                key_issues=[],
            )

        high_risk_query = (
            select(func.count())
            .select_from(Contract)
            .join(ContractAnalysis, ContractAnalysis.contract_id == Contract.id)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
            .where(ContractAnalysis.risk_score >= 70)
        )
        high_risk_result = await self.session.execute(high_risk_query)
        high_risk = high_risk_result.scalar() or 0

        top_issues_query = (
            select(Contract.filename, ContractAnalysis.risk_score)
            .select_from(Contract)
            .join(ContractAnalysis, ContractAnalysis.contract_id == Contract.id)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
            .where(ContractAnalysis.risk_score >= 70)
            .order_by(ContractAnalysis.risk_score.desc(), Contract.created_at.desc())
            .limit(3)
        )
        top_issues_result = await self.session.execute(top_issues_query)
        key_issues = [
            f"{filename}: Risiko-Score {risk_score}"
            for filename, risk_score in top_issues_result.all()
        ]

        score = int((high_risk / total) * 100)
        trend = await self._get_category_trend("contract_risk_score")

        return RiskCategory(
            name="Verträge",
            score=score,
            weight=self.WEIGHTS["contracts"],
            items_at_risk=high_risk,
            total_items=total,
            trend=trend,
            key_issues=key_issues,
        )

    async def _calculate_partner_risk(self) -> RiskCategory:
        """Calculate partner risk score using aggregates."""
        org_id = self._get_organization_id()

        total_query = (
            select(func.count())
            .select_from(Partner)
            .where(Partner.organization_id == org_id)
            .where(Partner.deleted_at.is_(None))
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return RiskCategory(
                name="Partner",
                score=0,
                weight=self.WEIGHTS["partners"],
                items_at_risk=0,
                total_items=0,
                trend="stable",
                key_issues=[],
            )

        high_risk_query = (
            select(func.count())
            .select_from(Partner)
            .where(Partner.organization_id == org_id)
            .where(Partner.deleted_at.is_(None))
            .where(Partner.risk_level.in_([PartnerRiskLevel.HIGH, PartnerRiskLevel.CRITICAL]))
        )
        high_risk_result = await self.session.execute(high_risk_query)
        high_risk = high_risk_result.scalar() or 0

        top_issues_query = (
            select(Partner.name, Partner.risk_level)
            .where(Partner.organization_id == org_id)
            .where(Partner.deleted_at.is_(None))
            .where(Partner.risk_level.in_([PartnerRiskLevel.HIGH, PartnerRiskLevel.CRITICAL]))
            .order_by(Partner.risk_score.desc().nullslast(), Partner.name.asc())
            .limit(3)
        )
        top_issues_result = await self.session.execute(top_issues_query)
        key_issues = [f"{name}: {risk_level.value}" for name, risk_level in top_issues_result.all()]

        score = int((high_risk / total) * 100)
        trend = await self._get_category_trend("partner_risk_score")

        return RiskCategory(
            name="Partner",
            score=score,
            weight=self.WEIGHTS["partners"],
            items_at_risk=high_risk,
            total_items=total,
            trend=trend,
            key_issues=key_issues,
        )

    async def _calculate_compliance_risk(self) -> RiskCategory:
        """Calculate compliance risk score using aggregates."""
        org_id = self._get_organization_id()

        total_contracts_query = (
            select(func.count())
            .select_from(Contract)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
        )
        total_contracts_result = await self.session.execute(total_contracts_query)
        total_contracts = total_contracts_result.scalar() or 0

        if total_contracts == 0:
            return RiskCategory(
                name="Compliance",
                score=0,
                weight=self.WEIGHTS["compliance"],
                items_at_risk=0,
                total_items=0,
                trend="stable",
                key_issues=[],
            )

        issues_contracts_query = (
            select(func.count(func.distinct(ComplianceCheck.contract_id)))
            .where(ComplianceCheck.organization_id == org_id)
            .where(ComplianceCheck.is_resolved.is_(False))
            .where(
                ComplianceCheck.status.in_(
                    [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.WARNING]
                )
            )
        )
        issues_contracts_result = await self.session.execute(issues_contracts_query)
        contracts_with_issues = issues_contracts_result.scalar() or 0

        top_issues_query = (
            select(ComplianceCheck.check_type, ComplianceCheck.title)
            .where(ComplianceCheck.organization_id == org_id)
            .where(ComplianceCheck.is_resolved.is_(False))
            .where(ComplianceCheck.status == ComplianceStatus.NON_COMPLIANT)
            .order_by(ComplianceCheck.checked_at.desc())
            .limit(3)
        )
        top_issues_result = await self.session.execute(top_issues_query)
        key_issues = [
            f"{check_type.value}: {title}" for check_type, title in top_issues_result.all()
        ]

        score = int((contracts_with_issues / total_contracts) * 100)
        trend = await self._get_category_trend("compliance_score")

        return RiskCategory(
            name="Compliance",
            score=score,
            weight=self.WEIGHTS["compliance"],
            items_at_risk=contracts_with_issues,
            total_items=total_contracts,
            trend=trend,
            key_issues=key_issues,
        )

    async def _calculate_deadline_risk(self) -> RiskCategory:
        """Calculate deadline risk score using aggregates."""
        org_id = self._get_organization_id()
        today = date.today()
        in_7_days = today + timedelta(days=7)

        total_query = (
            select(func.count())
            .select_from(ContractDeadline)
            .join(Contract, Contract.id == ContractDeadline.contract_id)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(Contract.deleted_at.is_(None))
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return RiskCategory(
                name="Fristen",
                score=0,
                weight=self.WEIGHTS["deadlines"],
                items_at_risk=0,
                total_items=0,
                trend="stable",
                key_issues=[],
            )

        overdue_query = (
            select(func.count())
            .select_from(ContractDeadline)
            .join(Contract, Contract.id == ContractDeadline.contract_id)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(ContractDeadline.deadline_date < today)
            .where(Contract.deleted_at.is_(None))
        )
        overdue_result = await self.session.execute(overdue_query)
        overdue = overdue_result.scalar() or 0

        urgent_query = (
            select(func.count())
            .select_from(ContractDeadline)
            .join(Contract, Contract.id == ContractDeadline.contract_id)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(ContractDeadline.deadline_date >= today)
            .where(ContractDeadline.deadline_date <= in_7_days)
            .where(Contract.deleted_at.is_(None))
        )
        urgent_result = await self.session.execute(urgent_query)
        urgent = urgent_result.scalar() or 0

        top_issues_query = (
            select(ContractDeadline.deadline_date, Contract.filename)
            .select_from(ContractDeadline)
            .join(Contract, Contract.id == ContractDeadline.contract_id)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(Contract.deleted_at.is_(None))
            .where(
                (ContractDeadline.deadline_date < today)
                | (
                    and_(
                        ContractDeadline.deadline_date >= today,
                        ContractDeadline.deadline_date <= in_7_days,
                    )
                )
            )
            .order_by(ContractDeadline.deadline_date.asc())
            .limit(3)
        )
        top_issues_result = await self.session.execute(top_issues_query)
        key_issues = []
        for deadline_date, filename in top_issues_result.all():
            days_until = (deadline_date - today).days
            if days_until < 0:
                key_issues.append(f"ÜBERFÄLLIG: {filename}")
            else:
                key_issues.append(f"{days_until} Tage: {filename}")

        score = min(100, (overdue * 20) + (urgent * 10))
        trend = await self._get_category_trend("pending_deadlines")

        return RiskCategory(
            name="Fristen",
            score=score,
            weight=self.WEIGHTS["deadlines"],
            items_at_risk=overdue + urgent,
            total_items=total,
            trend=trend,
            key_issues=key_issues,
        )

    async def _determine_overall_trend(self, current_score: int) -> str:
        """Determine trend by comparing to recent snapshots."""
        org_id = self._get_organization_id()
        yesterday = date.today() - timedelta(days=1)

        query = (
            select(RiskSnapshot)
            .where(RiskSnapshot.organization_id == org_id)
            .where(RiskSnapshot.snapshot_date == yesterday)
        )
        result = await self.session.execute(query)
        yesterday_snapshot = result.scalar_one_or_none()

        if not yesterday_snapshot:
            return "stable"

        diff = current_score - yesterday_snapshot.overall_risk_score
        if diff < -5:
            return "improving"
        elif diff > 5:
            return "worsening"
        else:
            return "stable"

    async def _get_category_trend(self, field_name: str) -> str:
        """Get trend for a specific category."""
        org_id = self._get_organization_id()
        yesterday = date.today() - timedelta(days=1)

        query = (
            select(RiskSnapshot)
            .where(RiskSnapshot.organization_id == org_id)
            .where(RiskSnapshot.snapshot_date == yesterday)
        )
        result = await self.session.execute(query)
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            return "stable"

        # Get the field value from snapshot
        yesterday_value = getattr(snapshot, field_name, None)
        if yesterday_value is None:
            return "stable"

        # We'd need current value to compare - for now return stable
        # This will be improved when we calculate during snapshot creation
        return "stable"

    async def _count_urgent_alerts(self) -> int:
        """Count urgent (new + critical/high) alerts."""
        org_id = self._get_organization_id()

        query = (
            select(func.count())
            .select_from(ProactiveAlert)
            .where(ProactiveAlert.organization_id == org_id)
            .where(ProactiveAlert.status.in_([AlertStatus.NEW, AlertStatus.SEEN]))
            .where(ProactiveAlert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.HIGH]))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _count_upcoming_deadlines(self) -> int:
        """Count deadlines in next 30 days."""
        org_id = self._get_organization_id()
        today = date.today()
        future = today + timedelta(days=30)

        query = (
            select(func.count())
            .select_from(ContractDeadline)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(ContractDeadline.deadline_date >= today)
            .where(ContractDeadline.deadline_date <= future)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    def _generate_recommendations(self, categories: list[RiskCategory]) -> list[str]:
        """Generate actionable recommendations based on risk scores."""
        recommendations = []

        for cat in categories:
            if cat.score >= 70:
                if cat.name == "Verträge":
                    recommendations.append(
                        f"⚠️ {cat.items_at_risk} Verträge mit hohem Risiko - "
                        "Prüfen Sie kritische Klauseln"
                    )
                elif cat.name == "Partner":
                    recommendations.append(
                        f"⚠️ {cat.items_at_risk} Partner mit hohem Risiko - "
                        "Bonitätsprüfung empfohlen"
                    )
                elif cat.name == "Compliance":
                    recommendations.append(
                        f"⚠️ {cat.items_at_risk} Compliance-Probleme - "
                        "Dringende Nachbesserung erforderlich"
                    )
                elif cat.name == "Fristen":
                    recommendations.append(
                        f"⚠️ {cat.items_at_risk} dringende Fristen - Sofortige Aktion erforderlich"
                    )
            elif cat.score >= 40 and cat.name == "Fristen":
                recommendations.append(
                    f"📅 {cat.items_at_risk} Fristen in den nächsten Wochen - Kalender prüfen"
                )

        if not recommendations:
            recommendations.append("✅ Alle Risikobereiche im grünen Bereich")

        return recommendations[:5]  # Max 5 recommendations

    # ─────────────────────────────────────────────────────────────
    #                  DAILY SNAPSHOTS
    # ─────────────────────────────────────────────────────────────

    async def create_daily_snapshot(self) -> RiskSnapshot:
        """Create a daily risk snapshot for trending.

        This should be called by the background worker once per day.
        """
        org_id = self._get_organization_id()
        today = date.today()

        # Check if snapshot already exists for today
        existing_query = (
            select(RiskSnapshot)
            .where(RiskSnapshot.organization_id == org_id)
            .where(RiskSnapshot.snapshot_date == today)
        )
        existing_result = await self.session.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            logger.info(
                "snapshot_already_exists",
                date=today.isoformat(),
            )
            return existing

        # Get current radar
        radar = await self.get_risk_radar()

        # Get counts
        contract_count = await self._get_total_contracts()
        partner_count = await self._get_total_partners()
        high_risk_contracts = await self._get_high_risk_contract_count()
        high_risk_partners = await self._get_high_risk_partner_count()
        pending_deadlines = await self._count_upcoming_deadlines()
        open_alerts = await self._get_open_alert_count()

        # Create snapshot
        snapshot = RiskSnapshot(
            id=uuid4(),
            organization_id=org_id,
            snapshot_date=today,
            overall_risk_score=radar.overall_score,
            contract_risk_score=next(
                (c.score for c in radar.categories if c.name == "Verträge"), 0
            ),
            partner_risk_score=next((c.score for c in radar.categories if c.name == "Partner"), 0),
            compliance_score=next((c.score for c in radar.categories if c.name == "Compliance"), 0),
            total_contracts=contract_count,
            high_risk_contracts=high_risk_contracts,
            total_partners=partner_count,
            high_risk_partners=high_risk_partners,
            pending_deadlines=pending_deadlines,
            open_alerts=open_alerts,
            details={
                "categories": [
                    {
                        "name": cat.name,
                        "score": cat.score,
                        "items_at_risk": cat.items_at_risk,
                        "total_items": cat.total_items,
                    }
                    for cat in radar.categories
                ],
                "recommendations": radar.recommendations,
            },
        )

        self.session.add(snapshot)
        await self.session.flush()

        logger.info(
            "daily_snapshot_created",
            date=today.isoformat(),
            overall_score=radar.overall_score,
        )

        return snapshot

    async def get_risk_history(
        self,
        days: int = 30,
    ) -> Sequence[RiskSnapshot]:
        """Get risk snapshots for the past N days."""
        org_id = self._get_organization_id()
        start_date = date.today() - timedelta(days=days)

        query = (
            select(RiskSnapshot)
            .where(RiskSnapshot.organization_id == org_id)
            .where(RiskSnapshot.snapshot_date >= start_date)
            .order_by(RiskSnapshot.snapshot_date.asc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────
    #                  HELPER METHODS
    # ─────────────────────────────────────────────────────────────

    async def _get_total_contracts(self) -> int:
        org_id = self._get_organization_id()
        query = (
            select(func.count())
            .select_from(Contract)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_total_partners(self) -> int:
        org_id = self._get_organization_id()
        query = (
            select(func.count())
            .select_from(Partner)
            .where(Partner.organization_id == org_id)
            .where(Partner.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_high_risk_contract_count(self) -> int:
        org_id = self._get_organization_id()
        query = (
            select(func.count())
            .select_from(Contract)
            .join(ContractAnalysis, ContractAnalysis.contract_id == Contract.id)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
            .where(ContractAnalysis.risk_score >= 70)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_high_risk_partner_count(self) -> int:
        org_id = self._get_organization_id()
        query = (
            select(func.count())
            .select_from(Partner)
            .where(Partner.organization_id == org_id)
            .where(Partner.deleted_at.is_(None))
            .where(Partner.risk_level.in_([PartnerRiskLevel.HIGH, PartnerRiskLevel.CRITICAL]))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_open_alert_count(self) -> int:
        org_id = self._get_organization_id()
        query = (
            select(func.count())
            .select_from(ProactiveAlert)
            .where(ProactiveAlert.organization_id == org_id)
            .where(
                ProactiveAlert.status.in_(
                    [AlertStatus.NEW, AlertStatus.SEEN, AlertStatus.IN_PROGRESS]
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
