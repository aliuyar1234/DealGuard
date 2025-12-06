"""Deadline extraction and monitoring service.

This service:
1. Extracts deadlines from contracts using AI
2. Stores them in the database
3. Monitors for upcoming deadlines
4. Generates alerts for approaching deadlines
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dealguard.infrastructure.ai.factory import get_ai_client
from dealguard.infrastructure.ai.prompts.deadline_extraction_v1 import (
    DeadlineExtractionPromptV1,
    DeadlineExtractionResult,
    ExtractedDeadline,
)
from dealguard.infrastructure.database.models.contract import Contract
from dealguard.infrastructure.database.models.proactive import (
    ContractDeadline,
    DeadlineType,
    DeadlineStatus,
    ProactiveAlert,
    AlertSourceType,
    AlertType,
    AlertSeverity,
    AlertStatus,
)
from dealguard.shared.context import get_tenant_context
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeadlineStats:
    """Statistics about deadlines."""

    total: int
    active: int
    overdue: int
    upcoming_7_days: int
    upcoming_30_days: int


class DeadlineService:
    """Service for extracting and monitoring contract deadlines.

    Flow:
    1. After contract analysis, extract deadlines using AI
    2. Store deadlines in database
    3. Background worker checks daily for approaching deadlines
    4. Generate alerts for deadlines needing attention
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai_client = get_ai_client()
        self.prompt = DeadlineExtractionPromptV1()

    def _get_organization_id(self) -> UUID:
        return get_tenant_context().organization_id

    # ─────────────────────────────────────────────────────────────
    #                  DEADLINE EXTRACTION
    # ─────────────────────────────────────────────────────────────

    async def extract_deadlines_from_contract(
        self,
        contract_id: UUID,
    ) -> list[ContractDeadline]:
        """Extract all deadlines from a contract using AI.

        This should be called after contract analysis completes.
        """
        org_id = self._get_organization_id()

        # Get contract
        query = (
            select(Contract)
            .where(Contract.id == contract_id)
            .where(Contract.organization_id == org_id)
        )
        result = await self.session.execute(query)
        contract = result.scalar_one_or_none()

        if not contract or not contract.raw_text:
            logger.warning(
                "contract_not_found_for_deadline_extraction",
                contract_id=str(contract_id),
            )
            return []

        # Call AI for extraction
        system_prompt = self.prompt.render_system()
        user_prompt = self.prompt.render_user(
            contract_text=contract.raw_text[:15000],  # Limit to avoid token limits
            contract_filename=contract.filename,
            reference_date=date.today(),
        )

        logger.info(
            "extracting_deadlines",
            contract_id=str(contract_id),
            filename=contract.filename,
        )

        ai_response = await self.ai_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # Low for factual extraction
            action="deadline_extraction",
            resource_id=contract_id,
        )

        # Parse response
        extraction_result = self.prompt.parse_response(ai_response.content)

        # Store deadlines
        deadlines = await self._store_deadlines(
            contract_id=contract_id,
            extraction_result=extraction_result,
            ai_model=ai_response.model,
        )

        # Update contract metadata with extraction info
        contract.contract_metadata = {
            **contract.contract_metadata,
            "deadline_extraction": {
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "deadline_count": len(deadlines),
                "has_auto_renewal": extraction_result.has_auto_renewal,
                "auto_renewal_period": extraction_result.auto_renewal_period,
                "termination_notice_period": extraction_result.termination_notice_period,
                "warnings": extraction_result.warnings,
            },
        }
        await self.session.flush()

        logger.info(
            "deadlines_extracted",
            contract_id=str(contract_id),
            deadline_count=len(deadlines),
            has_auto_renewal=extraction_result.has_auto_renewal,
        )

        return deadlines

    async def _store_deadlines(
        self,
        contract_id: UUID,
        extraction_result: DeadlineExtractionResult,
        ai_model: str,
    ) -> list[ContractDeadline]:
        """Store extracted deadlines in database."""
        org_id = self._get_organization_id()
        deadlines = []

        for extracted in extraction_result.deadlines:
            # Parse date
            try:
                deadline_date = date.fromisoformat(extracted.deadline_date)
            except ValueError:
                logger.warning(
                    "invalid_deadline_date",
                    date_str=extracted.deadline_date,
                    contract_id=str(contract_id),
                )
                continue

            # Map deadline type
            deadline_type = self._map_deadline_type(extracted.deadline_type)

            deadline = ContractDeadline(
                id=uuid4(),
                organization_id=org_id,
                contract_id=contract_id,
                deadline_type=deadline_type,
                deadline_date=deadline_date,
                reminder_days_before=extracted.reminder_days,
                source_clause=extracted.source_clause,
                clause_location=extracted.clause_location,
                confidence=extracted.confidence,
                extracted_by_model=ai_model,
                status=DeadlineStatus.ACTIVE,
            )

            self.session.add(deadline)
            deadlines.append(deadline)

        await self.session.flush()
        return deadlines

    def _map_deadline_type(self, type_str: str) -> DeadlineType:
        """Map string to DeadlineType enum."""
        mapping = {
            "termination_notice": DeadlineType.TERMINATION_NOTICE,
            "auto_renewal": DeadlineType.AUTO_RENEWAL,
            "contract_end": DeadlineType.CONTRACT_END,
            "payment_due": DeadlineType.PAYMENT_DUE,
            "warranty_end": DeadlineType.WARRANTY_END,
            "price_adjustment": DeadlineType.PRICE_ADJUSTMENT,
            "review_date": DeadlineType.REVIEW_DATE,
            "notice_period": DeadlineType.NOTICE_PERIOD,
        }
        return mapping.get(type_str.lower(), DeadlineType.OTHER)

    # ─────────────────────────────────────────────────────────────
    #                  DEADLINE MONITORING
    # ─────────────────────────────────────────────────────────────

    async def get_upcoming_deadlines(
        self,
        days_ahead: int = 30,
        limit: int = 50,
    ) -> Sequence[ContractDeadline]:
        """Get upcoming deadlines for the organization."""
        org_id = self._get_organization_id()
        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        query = (
            select(ContractDeadline)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(ContractDeadline.deadline_date >= today)
            .where(ContractDeadline.deadline_date <= future_date)
            .options(selectinload(ContractDeadline.contract))
            .order_by(ContractDeadline.deadline_date.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_overdue_deadlines(
        self,
        limit: int = 50,
    ) -> Sequence[ContractDeadline]:
        """Get overdue (missed) deadlines."""
        org_id = self._get_organization_id()
        today = date.today()

        query = (
            select(ContractDeadline)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .where(ContractDeadline.deadline_date < today)
            .options(selectinload(ContractDeadline.contract))
            .order_by(ContractDeadline.deadline_date.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_deadline_stats(self) -> DeadlineStats:
        """Get deadline statistics for the organization."""
        org_id = self._get_organization_id()
        today = date.today()

        # Get all active deadlines
        query = (
            select(ContractDeadline)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
        )
        result = await self.session.execute(query)
        deadlines = result.scalars().all()

        total = len(deadlines)
        overdue = sum(1 for d in deadlines if d.deadline_date < today)
        upcoming_7 = sum(
            1 for d in deadlines
            if today <= d.deadline_date <= today + timedelta(days=7)
        )
        upcoming_30 = sum(
            1 for d in deadlines
            if today <= d.deadline_date <= today + timedelta(days=30)
        )

        return DeadlineStats(
            total=total,
            active=total - overdue,
            overdue=overdue,
            upcoming_7_days=upcoming_7,
            upcoming_30_days=upcoming_30,
        )

    async def get_deadlines_for_contract(
        self,
        contract_id: UUID,
    ) -> Sequence[ContractDeadline]:
        """Get all deadlines for a specific contract."""
        org_id = self._get_organization_id()

        query = (
            select(ContractDeadline)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.contract_id == contract_id)
            .order_by(ContractDeadline.deadline_date.asc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────
    #                  DEADLINE ACTIONS
    # ─────────────────────────────────────────────────────────────

    async def mark_deadline_handled(
        self,
        deadline_id: UUID,
        action: str,
        notes: str | None = None,
    ) -> ContractDeadline | None:
        """Mark a deadline as handled."""
        org_id = self._get_organization_id()
        user_id = get_tenant_context().user_id

        query = (
            select(ContractDeadline)
            .where(ContractDeadline.id == deadline_id)
            .where(ContractDeadline.organization_id == org_id)
        )
        result = await self.session.execute(query)
        deadline = result.scalar_one_or_none()

        if not deadline:
            return None

        deadline.status = DeadlineStatus.HANDLED
        deadline.handled_at = datetime.now(timezone.utc)
        deadline.handled_by = user_id
        deadline.handled_action = action
        deadline.notes = notes

        await self.session.flush()

        logger.info(
            "deadline_marked_handled",
            deadline_id=str(deadline_id),
            action=action,
        )

        return deadline

    async def dismiss_deadline(
        self,
        deadline_id: UUID,
        notes: str | None = None,
    ) -> ContractDeadline | None:
        """Dismiss a deadline (mark as not relevant)."""
        return await self.mark_deadline_handled(
            deadline_id=deadline_id,
            action="dismissed",
            notes=notes,
        )

    async def verify_deadline(
        self,
        deadline_id: UUID,
        correct_date: date | None = None,
    ) -> ContractDeadline | None:
        """Verify an AI-extracted deadline (human confirmation)."""
        org_id = self._get_organization_id()

        query = (
            select(ContractDeadline)
            .where(ContractDeadline.id == deadline_id)
            .where(ContractDeadline.organization_id == org_id)
        )
        result = await self.session.execute(query)
        deadline = result.scalar_one_or_none()

        if not deadline:
            return None

        deadline.is_verified = True
        if correct_date:
            deadline.deadline_date = correct_date
            deadline.confidence = 1.0  # Human verified = 100% confidence

        await self.session.flush()

        logger.info(
            "deadline_verified",
            deadline_id=str(deadline_id),
        )

        return deadline

    # ─────────────────────────────────────────────────────────────
    #              ALERT GENERATION (called by worker)
    # ─────────────────────────────────────────────────────────────

    async def check_and_generate_alerts(self) -> list[ProactiveAlert]:
        """Check deadlines and generate alerts for those needing attention.

        This is called by the background worker daily.
        """
        org_id = self._get_organization_id()
        today = date.today()
        alerts_generated = []

        # Get all active deadlines
        query = (
            select(ContractDeadline)
            .where(ContractDeadline.organization_id == org_id)
            .where(ContractDeadline.status == DeadlineStatus.ACTIVE)
            .options(selectinload(ContractDeadline.contract))
        )
        result = await self.session.execute(query)
        deadlines = result.scalars().all()

        for deadline in deadlines:
            days_until = (deadline.deadline_date - today).days

            # Check if within reminder period
            if days_until <= deadline.reminder_days_before and days_until >= 0:
                # Check if we already have an alert for this deadline
                existing_alert = await self._get_existing_alert(deadline.id)
                if existing_alert:
                    continue

                # Generate alert
                alert = await self._create_deadline_alert(deadline, days_until)
                alerts_generated.append(alert)

            # Check for overdue
            elif days_until < 0:
                # Mark as expired if not handled
                deadline.status = DeadlineStatus.EXPIRED

                # Generate critical alert
                existing_alert = await self._get_existing_alert(deadline.id)
                if not existing_alert:
                    alert = await self._create_overdue_alert(deadline, abs(days_until))
                    alerts_generated.append(alert)

        await self.session.flush()

        if alerts_generated:
            logger.info(
                "deadline_alerts_generated",
                alert_count=len(alerts_generated),
                organization_id=str(org_id),
            )

        return alerts_generated

    async def _get_existing_alert(self, deadline_id: UUID) -> ProactiveAlert | None:
        """Check if an alert already exists for this deadline."""
        org_id = self._get_organization_id()

        query = (
            select(ProactiveAlert)
            .where(ProactiveAlert.organization_id == org_id)
            .where(ProactiveAlert.source_type == AlertSourceType.DEADLINE)
            .where(ProactiveAlert.source_id == deadline_id)
            .where(ProactiveAlert.status.in_([
                AlertStatus.NEW, AlertStatus.SEEN, AlertStatus.IN_PROGRESS
            ]))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _create_deadline_alert(
        self,
        deadline: ContractDeadline,
        days_until: int,
    ) -> ProactiveAlert:
        """Create an alert for an approaching deadline."""
        org_id = self._get_organization_id()

        # Determine severity based on days remaining
        if days_until <= 7:
            severity = AlertSeverity.HIGH
        elif days_until <= 14:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW

        # Determine alert type
        if deadline.deadline_type == DeadlineType.AUTO_RENEWAL:
            alert_type = AlertType.AUTO_RENEWAL_WARNING
            title = f"Automatische Verlängerung in {days_until} Tagen"
            recommendation = (
                "Prüfen Sie, ob Sie den Vertrag fortführen möchten. "
                "Falls nicht, müssen Sie rechtzeitig kündigen."
            )
        elif deadline.deadline_type == DeadlineType.TERMINATION_NOTICE:
            alert_type = AlertType.DEADLINE_APPROACHING
            title = f"Kündigungsfrist endet in {days_until} Tagen"
            recommendation = (
                "Entscheiden Sie, ob Sie kündigen möchten. "
                "Nach Ablauf der Frist ist keine Kündigung mehr möglich."
            )
        elif deadline.deadline_type == DeadlineType.PAYMENT_DUE:
            alert_type = AlertType.PAYMENT_DUE
            title = f"Zahlung fällig in {days_until} Tagen"
            recommendation = "Stellen Sie sicher, dass die Zahlung rechtzeitig erfolgt."
        else:
            alert_type = AlertType.DEADLINE_APPROACHING
            title = f"Frist in {days_until} Tagen: {deadline.deadline_type.value}"
            recommendation = "Prüfen Sie die erforderliche Aktion."

        # Build recommended actions
        actions = [
            {"action": "view_contract", "label": "Vertrag ansehen"},
            {"action": "mark_handled", "label": "Als erledigt markieren"},
            {"action": "snooze", "label": "Später erinnern"},
        ]

        if deadline.deadline_type in (DeadlineType.TERMINATION_NOTICE, DeadlineType.AUTO_RENEWAL):
            actions.insert(0, {"action": "generate_termination", "label": "Kündigung vorbereiten"})

        alert = ProactiveAlert(
            id=uuid4(),
            organization_id=org_id,
            source_type=AlertSourceType.DEADLINE,
            source_id=deadline.id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=f"Vertrag: {deadline.contract.filename}\n\n"
                       f"Frist: {deadline.deadline_date.strftime('%d.%m.%Y')}\n"
                       f"Klausel: {deadline.source_clause or 'Nicht verfügbar'}",
            ai_recommendation=recommendation,
            recommended_actions=actions,
            related_contract_id=deadline.contract_id,
            status=AlertStatus.NEW,
            due_date=deadline.deadline_date,
        )

        self.session.add(alert)
        return alert

    async def _create_overdue_alert(
        self,
        deadline: ContractDeadline,
        days_overdue: int,
    ) -> ProactiveAlert:
        """Create a critical alert for an overdue deadline."""
        org_id = self._get_organization_id()

        alert = ProactiveAlert(
            id=uuid4(),
            organization_id=org_id,
            source_type=AlertSourceType.DEADLINE,
            source_id=deadline.id,
            alert_type=AlertType.DEADLINE_APPROACHING,
            severity=AlertSeverity.CRITICAL,
            title=f"ÜBERFÄLLIG: Frist seit {days_overdue} Tagen abgelaufen",
            description=f"Vertrag: {deadline.contract.filename}\n\n"
                       f"Frist war: {deadline.deadline_date.strftime('%d.%m.%Y')}\n"
                       f"Typ: {deadline.deadline_type.value}",
            ai_recommendation="Diese Frist ist bereits abgelaufen. Prüfen Sie die Konsequenzen.",
            recommended_actions=[
                {"action": "view_contract", "label": "Vertrag ansehen"},
                {"action": "mark_handled", "label": "Als geklärt markieren"},
            ],
            related_contract_id=deadline.contract_id,
            status=AlertStatus.NEW,
        )

        self.session.add(alert)
        return alert
