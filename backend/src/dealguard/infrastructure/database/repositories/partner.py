"""Partner repositories."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from dealguard.infrastructure.database.models.partner import (
    CheckStatus,
    ContractPartner,
    Partner,
    PartnerAlert,
    PartnerCheck,
    PartnerRiskLevel,
)
from dealguard.infrastructure.database.repositories.base import BaseRepository


class PartnerRepository(BaseRepository[Partner]):
    """Repository for Partner entities."""

    model_class = Partner

    async def get_by_id_with_details(self, partner_id: UUID) -> Partner | None:
        """Get partner with checks, alerts, and contract links."""
        query = (
            self._base_query()
            .where(Partner.id == partner_id)
            .where(Partner.deleted_at.is_(None))
            .options(
                selectinload(Partner.checks),
                selectinload(Partner.alerts),
                selectinload(Partner.contract_links).selectinload(ContractPartner.contract),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Sequence[Partner]:
        """Get all partners for the current tenant."""
        query = self._base_query().order_by(Partner.name.asc())

        if not include_deleted:
            query = query.where(Partner.deleted_at.is_(None))

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, include_deleted: bool = False) -> int:
        """Count partners for the current tenant."""
        base = self._base_query()
        if not include_deleted:
            base = base.where(Partner.deleted_at.is_(None))
        query = select(func.count()).select_from(base.subquery())
        result = await self.session.execute(query)
        return result.scalar_one()

    async def search(
        self,
        query_str: str,
        *,
        limit: int = 20,
    ) -> Sequence[Partner]:
        """Search partners by name or identifiers."""
        search_pattern = f"%{query_str}%"
        query = (
            self._base_query()
            .where(Partner.deleted_at.is_(None))
            .where(
                or_(
                    Partner.name.ilike(search_pattern),
                    Partner.handelsregister_id.ilike(search_pattern),
                    Partner.vat_id.ilike(search_pattern),
                    Partner.city.ilike(search_pattern),
                )
            )
            .order_by(Partner.name.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_handelsregister_id(self, hr_id: str) -> Partner | None:
        """Find partner by Handelsregister ID."""
        query = (
            self._base_query()
            .where(Partner.deleted_at.is_(None))
            .where(Partner.handelsregister_id == hr_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_watched_partners(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Partner]:
        """Get partners on the watchlist."""
        query = (
            self._base_query()
            .where(Partner.deleted_at.is_(None))
            .where(Partner.is_watched.is_(True))
            .order_by(Partner.name.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_high_risk_partners(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Partner]:
        """Get partners with high or critical risk level."""
        query = (
            self._base_query()
            .where(Partner.deleted_at.is_(None))
            .where(Partner.risk_level.in_([PartnerRiskLevel.HIGH, PartnerRiskLevel.CRITICAL]))
            .order_by(Partner.risk_score.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_risk_assessment(
        self,
        partner: Partner,
        risk_score: int,
        risk_level: PartnerRiskLevel,
    ) -> Partner:
        """Update partner's risk assessment."""
        partner.risk_score = risk_score
        partner.risk_level = risk_level
        partner.last_check_at = datetime.now(UTC)
        return await self.update(partner)


class PartnerCheckRepository(BaseRepository[PartnerCheck]):
    """Repository for PartnerCheck entities."""

    model_class = PartnerCheck

    async def get_by_partner_id(
        self,
        partner_id: UUID,
        *,
        limit: int = 10,
    ) -> Sequence[PartnerCheck]:
        """Get all checks for a partner."""
        query = (
            self._base_query()
            .where(PartnerCheck.partner_id == partner_id)
            .order_by(PartnerCheck.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_latest_by_type(
        self,
        partner_id: UUID,
        check_type: str,
    ) -> PartnerCheck | None:
        """Get the latest check of a specific type."""
        query = (
            self._base_query()
            .where(PartnerCheck.partner_id == partner_id)
            .where(PartnerCheck.check_type == check_type)
            .where(PartnerCheck.status == CheckStatus.COMPLETED)
            .order_by(PartnerCheck.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        check: PartnerCheck,
        status: CheckStatus,
        error_message: str | None = None,
    ) -> PartnerCheck:
        """Update check status."""
        check.status = status
        if error_message:
            check.error_message = error_message
        return await self.update(check)


class PartnerAlertRepository(BaseRepository[PartnerAlert]):
    """Repository for PartnerAlert entities."""

    model_class = PartnerAlert

    async def get_by_partner_id(
        self,
        partner_id: UUID,
        *,
        limit: int = 20,
        include_dismissed: bool = False,
    ) -> Sequence[PartnerAlert]:
        """Get alerts for a partner."""
        query = (
            self._base_query()
            .where(PartnerAlert.partner_id == partner_id)
            .order_by(PartnerAlert.created_at.desc())
        )
        if not include_dismissed:
            query = query.where(PartnerAlert.is_dismissed.is_(False))
        query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_unread_count(self) -> int:
        """Get count of unread alerts for the organization."""
        query = select(func.count()).select_from(
            self._base_query()
            .where(PartnerAlert.is_read.is_(False))
            .where(PartnerAlert.is_dismissed.is_(False))
            .subquery()
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_all_unread(self, *, limit: int = 50) -> Sequence[PartnerAlert]:
        """Get all unread alerts."""
        query = (
            self._base_query()
            .where(PartnerAlert.is_read.is_(False))
            .where(PartnerAlert.is_dismissed.is_(False))
            .order_by(PartnerAlert.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def mark_as_read(self, alert: PartnerAlert) -> PartnerAlert:
        """Mark alert as read."""
        alert.is_read = True
        return await self.update(alert)

    async def dismiss(self, alert: PartnerAlert, user_id: UUID) -> PartnerAlert:
        """Dismiss an alert."""
        alert.is_dismissed = True
        alert.dismissed_at = datetime.now(UTC)
        alert.dismissed_by = user_id
        return await self.update(alert)


class ContractPartnerRepository(BaseRepository[ContractPartner]):
    """Repository for ContractPartner junction entities."""

    model_class = ContractPartner

    async def get_by_contract_id(self, contract_id: UUID) -> Sequence[ContractPartner]:
        """Get all partner links for a contract."""
        query = (
            self._base_query()
            .where(ContractPartner.contract_id == contract_id)
            .options(selectinload(ContractPartner.partner))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_partner_id(self, partner_id: UUID) -> Sequence[ContractPartner]:
        """Get all contract links for a partner."""
        query = (
            self._base_query()
            .where(ContractPartner.partner_id == partner_id)
            .options(selectinload(ContractPartner.contract))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def link_exists(self, contract_id: UUID, partner_id: UUID) -> bool:
        """Check if a contract-partner link already exists."""
        query = (
            self._base_query()
            .where(ContractPartner.contract_id == contract_id)
            .where(ContractPartner.partner_id == partner_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def remove_link(self, contract_id: UUID, partner_id: UUID) -> bool:
        """Remove a contract-partner link."""
        query = (
            self._base_query()
            .where(ContractPartner.contract_id == contract_id)
            .where(ContractPartner.partner_id == partner_id)
        )
        result = await self.session.execute(query)
        link = result.scalar_one_or_none()
        if link:
            await self.delete(link)
            return True
        return False
