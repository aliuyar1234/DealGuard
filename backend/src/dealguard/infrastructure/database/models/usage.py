"""Usage tracking model for billing."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from dealguard.infrastructure.database.models.base import (
    Base,
    TenantMixin,
    TimestampMixin,
)


class UsageAction(str, Enum):
    """Types of billable actions."""

    CONTRACT_ANALYSIS = "contract_analysis"
    PARTNER_CHECK = "partner_check"
    ALERT_SCAN = "alert_scan"
    API_CALL = "api_call"


class UsageLog(Base, TenantMixin, TimestampMixin):
    """Usage log for billing and analytics.

    Tracks every billable action with token usage and cost.
    Partitioned by billing_period for efficient queries.
    """

    __tablename__ = "usage_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Who performed the action
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    api_key_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )  # For API access tracking

    # What action
    action: Mapped[UsageAction] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "contract"
    resource_id: Mapped[UUID | None] = mapped_column(nullable=True)

    # AI usage
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost
    cost_cents: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Billing period (for efficient aggregation)
    billing_period: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True
    )  # YYYY-MM

    def __repr__(self) -> str:
        return f"<UsageLog {self.action} {self.created_at}>"
