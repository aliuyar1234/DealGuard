"""Organization model for multi-tenancy."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealguard.infrastructure.database.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from dealguard.infrastructure.database.models.user import User
    from dealguard.infrastructure.database.models.contract import Contract
    from dealguard.infrastructure.database.models.partner import Partner


class PlanTier(str, Enum):
    """Subscription plan tiers."""

    STARTER = "starter"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """Organization/tenant model.

    This is the root entity for multi-tenancy. All other tenant-scoped
    models reference this through organization_id.
    """

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Billing
    plan_tier: Mapped[PlanTier] = mapped_column(
        String(50),
        default=PlanTier.STARTER,
        nullable=False,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Settings (flexible JSON for org-specific config)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    partners: Mapped[list["Partner"]] = relationship(
        "Partner",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"

    # Plan limits
    @property
    def contract_limit(self) -> int:
        """Monthly contract analysis limit."""
        limits = {
            PlanTier.STARTER: 10,
            PlanTier.BUSINESS: 50,
            PlanTier.ENTERPRISE: 999999,  # Unlimited
        }
        return limits[self.plan_tier]

    @property
    def partner_limit(self) -> int:
        """Monthly partner check limit."""
        limits = {
            PlanTier.STARTER: 5,
            PlanTier.BUSINESS: 25,
            PlanTier.ENTERPRISE: 999999,
        }
        return limits[self.plan_tier]

    @property
    def watchlist_limit(self) -> int:
        """Watchlist partner limit."""
        limits = {
            PlanTier.STARTER: 0,
            PlanTier.BUSINESS: 10,
            PlanTier.ENTERPRISE: 999999,
        }
        return limits[self.plan_tier]
