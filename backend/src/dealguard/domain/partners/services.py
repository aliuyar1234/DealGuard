"""Partner intelligence service - core business logic."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from dealguard.domain.partners.risk_calculator import PartnerRiskCalculator
from dealguard.infrastructure.database.models.partner import (
    AlertSeverity,
    AlertType,
    CheckStatus,
    CheckType,
    ContractPartner,
    Partner,
    PartnerAlert,
    PartnerCheck,
    PartnerType,
)
from dealguard.infrastructure.database.repositories.partner import (
    ContractPartnerRepository,
    PartnerAlertRepository,
    PartnerCheckRepository,
    PartnerRepository,
)
from dealguard.shared.exceptions import NotFoundError, ValidationError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


class PartnerService:
    """Service for partner intelligence operations.

    This is the main entry point for partner-related business logic.
    It handles CRUD operations, risk assessment, and contract linking.
    """

    def __init__(
        self,
        partner_repo: PartnerRepository,
        check_repo: PartnerCheckRepository,
        alert_repo: PartnerAlertRepository,
        contract_partner_repo: ContractPartnerRepository,
    ) -> None:
        self.partner_repo = partner_repo
        self.check_repo = check_repo
        self.alert_repo = alert_repo
        self.contract_partner_repo = contract_partner_repo
        self.risk_calculator = PartnerRiskCalculator()

    # ----- Partner CRUD -----

    async def create_partner(
        self,
        name: str,
        partner_type: PartnerType = PartnerType.OTHER,
        *,
        created_by: UUID,
        handelsregister_id: str | None = None,
        tax_id: str | None = None,
        vat_id: str | None = None,
        street: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        country: str = "DE",
        website: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
    ) -> Partner:
        """Create a new partner."""
        # Check for duplicate by Handelsregister ID
        if handelsregister_id:
            existing = await self.partner_repo.get_by_handelsregister_id(handelsregister_id)
            if existing:
                logger.info(
                    "duplicate_partner_by_hr_id",
                    handelsregister_id=handelsregister_id,
                    existing_id=str(existing.id),
                )
                return existing

        partner = Partner(
            created_by=created_by,
            name=name,
            partner_type=partner_type,
            handelsregister_id=handelsregister_id,
            tax_id=tax_id,
            vat_id=vat_id,
            street=street,
            city=city,
            postal_code=postal_code,
            country=country,
            website=website,
            email=email,
            phone=phone,
            notes=notes,
        )

        partner = await self.partner_repo.create(partner)

        logger.info(
            "partner_created",
            partner_id=str(partner.id),
            name=name,
        )

        return partner

    async def get_partner(self, partner_id: UUID) -> Partner | None:
        """Get a partner by ID with all details."""
        return await self.partner_repo.get_by_id_with_details(partner_id)

    async def list_partners(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Partner]:
        """List partners for the current organization."""
        return await self.partner_repo.get_all(limit=limit, offset=offset)

    async def search_partners(self, query: str, limit: int = 20) -> Sequence[Partner]:
        """Search partners by name or identifiers."""
        return await self.partner_repo.search(query, limit=limit)

    async def update_partner(
        self,
        partner_id: UUID,
        *,
        name: str | None = None,
        partner_type: PartnerType | None = None,
        handelsregister_id: str | None = None,
        tax_id: str | None = None,
        vat_id: str | None = None,
        street: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        website: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        notes: str | None = None,
        is_watched: bool | None = None,
    ) -> Partner:
        """Update partner details."""
        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Update fields if provided
        if name is not None:
            partner.name = name
        if partner_type is not None:
            partner.partner_type = partner_type
        if handelsregister_id is not None:
            partner.handelsregister_id = handelsregister_id
        if tax_id is not None:
            partner.tax_id = tax_id
        if vat_id is not None:
            partner.vat_id = vat_id
        if street is not None:
            partner.street = street
        if city is not None:
            partner.city = city
        if postal_code is not None:
            partner.postal_code = postal_code
        if country is not None:
            partner.country = country
        if website is not None:
            partner.website = website
        if email is not None:
            partner.email = email
        if phone is not None:
            partner.phone = phone
        if notes is not None:
            partner.notes = notes
        if is_watched is not None:
            partner.is_watched = is_watched

        partner = await self.partner_repo.update(partner)

        logger.info("partner_updated", partner_id=str(partner_id))

        return partner

    async def delete_partner(self, partner_id: UUID) -> None:
        """Soft delete a partner."""
        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        await self.partner_repo.soft_delete(partner)

        logger.info("partner_deleted", partner_id=str(partner_id))

    # ----- Risk Assessment -----

    async def calculate_risk_score(self, partner_id: UUID) -> Partner:
        """Calculate and update partner's risk score based on available checks."""
        partner = await self.partner_repo.get_by_id_with_details(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Get completed checks
        completed_checks = [c for c in partner.checks if c.status == CheckStatus.COMPLETED]

        # Calculate risk score
        risk_score, risk_level = self.risk_calculator.calculate(completed_checks)

        # Update partner
        partner = await self.partner_repo.update_risk_assessment(partner, risk_score, risk_level)

        logger.info(
            "partner_risk_calculated",
            partner_id=str(partner_id),
            risk_score=risk_score,
            risk_level=risk_level.value,
        )

        return partner

    async def get_high_risk_partners(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Partner]:
        """Get high-risk partners."""
        return await self.partner_repo.get_high_risk_partners(limit=limit, offset=offset)

    async def get_watched_partners(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Partner]:
        """Get watched partners."""
        return await self.partner_repo.get_watched_partners(limit=limit, offset=offset)

    # ----- Contract Linking -----

    async def link_to_contract(
        self,
        partner_id: UUID,
        contract_id: UUID,
        role: str | None = None,
        notes: str | None = None,
    ) -> ContractPartner:
        """Link a partner to a contract."""
        # Verify partner exists
        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Check if link already exists
        if await self.contract_partner_repo.link_exists(contract_id, partner_id):
            raise ValidationError("Partner ist bereits mit diesem Vertrag verknüpft")

        link = ContractPartner(
            contract_id=contract_id,
            partner_id=partner_id,
            role=role,
            notes=notes,
        )

        link = await self.contract_partner_repo.create(link)

        logger.info(
            "partner_linked_to_contract",
            partner_id=str(partner_id),
            contract_id=str(contract_id),
        )

        return link

    async def unlink_from_contract(
        self,
        partner_id: UUID,
        contract_id: UUID,
    ) -> bool:
        """Unlink a partner from a contract."""
        removed = await self.contract_partner_repo.remove_link(contract_id, partner_id)

        if removed:
            logger.info(
                "partner_unlinked_from_contract",
                partner_id=str(partner_id),
                contract_id=str(contract_id),
            )

        return removed

    async def get_partners_for_contract(
        self,
        contract_id: UUID,
    ) -> Sequence[ContractPartner]:
        """Get all partners linked to a contract."""
        return await self.contract_partner_repo.get_by_contract_id(contract_id)

    async def get_contracts_for_partner(
        self,
        partner_id: UUID,
    ) -> Sequence[ContractPartner]:
        """Get all contracts linked to a partner."""
        return await self.contract_partner_repo.get_by_partner_id(partner_id)

    # ----- Alerts -----

    async def get_alerts_for_partner(
        self,
        partner_id: UUID,
        include_dismissed: bool = False,
    ) -> Sequence[PartnerAlert]:
        """Get alerts for a partner."""
        return await self.alert_repo.get_by_partner_id(
            partner_id, include_dismissed=include_dismissed
        )

    async def get_all_unread_alerts(self) -> Sequence[PartnerAlert]:
        """Get all unread alerts for the organization."""
        return await self.alert_repo.get_all_unread()

    async def get_unread_alert_count(self) -> int:
        """Get count of unread alerts."""
        return await self.alert_repo.get_unread_count()

    async def mark_alert_read(self, alert_id: UUID) -> PartnerAlert:
        """Mark an alert as read."""
        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert", str(alert_id))

        return await self.alert_repo.mark_as_read(alert)

    async def dismiss_alert(self, alert_id: UUID, *, dismissed_by: UUID) -> PartnerAlert:
        """Dismiss an alert."""
        alert = await self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert", str(alert_id))

        return await self.alert_repo.dismiss(alert, dismissed_by)

    async def create_alert(
        self,
        partner_id: UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        source: str | None = None,
        source_url: str | None = None,
    ) -> PartnerAlert:
        """Create a new alert for a partner."""
        alert = PartnerAlert(
            partner_id=partner_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            source=source,
            source_url=source_url,
        )

        alert = await self.alert_repo.create(alert)

        logger.info(
            "partner_alert_created",
            partner_id=str(partner_id),
            alert_type=alert_type.value,
            severity=severity.value,
        )

        return alert

    # ----- Partner Checks -----

    async def create_check(
        self,
        partner_id: UUID,
        check_type: CheckType,
        provider: str | None = None,
    ) -> PartnerCheck:
        """Create a new pending check for a partner."""
        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        check = PartnerCheck(
            partner_id=partner_id,
            check_type=check_type,
            status=CheckStatus.PENDING,
            provider=provider,
        )

        check = await self.check_repo.create(check)

        logger.info(
            "partner_check_created",
            partner_id=str(partner_id),
            check_type=check_type.value,
        )

        return check

    async def complete_check(
        self,
        check: PartnerCheck,
        score: int | None,
        result_summary: str,
        raw_response: dict[str, Any],
        provider_reference: str | None = None,
    ) -> PartnerCheck:
        """Complete a check with results."""
        check.status = CheckStatus.COMPLETED
        check.score = score
        check.result_summary = result_summary
        check.raw_response = raw_response
        check.provider_reference = provider_reference

        check = await self.check_repo.update(check)

        logger.info(
            "partner_check_completed",
            check_id=str(check.id),
            check_type=check.check_type,
            score=score,
        )

        return check

    async def fail_check(
        self,
        check: PartnerCheck,
        error_message: str,
    ) -> PartnerCheck:
        """Mark a check as failed."""
        return await self.check_repo.update_status(check, CheckStatus.FAILED, error_message)

    async def get_checks_for_partner(
        self,
        partner_id: UUID,
    ) -> Sequence[PartnerCheck]:
        """Get all checks for a partner."""
        return await self.check_repo.get_by_partner_id(partner_id)
