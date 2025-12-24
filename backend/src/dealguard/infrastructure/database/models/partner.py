"""Partner and partner intelligence models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealguard.infrastructure.database.models.base import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from dealguard.infrastructure.database.models.contract import Contract
    from dealguard.infrastructure.database.models.organization import Organization
    from dealguard.infrastructure.database.models.user import User


class PartnerType(str, Enum):
    """Type of business partner."""

    SUPPLIER = "supplier"  # Lieferant
    CUSTOMER = "customer"  # Kunde
    SERVICE_PROVIDER = "service_provider"  # Dienstleister
    DISTRIBUTOR = "distributor"  # Distributor/Vertrieb
    PARTNER = "partner"  # Geschäftspartner
    OTHER = "other"


class PartnerRiskLevel(str, Enum):
    """Risk level classification for partners."""

    LOW = "low"  # 0-30
    MEDIUM = "medium"  # 31-60
    HIGH = "high"  # 61-80
    CRITICAL = "critical"  # 81-100
    UNKNOWN = "unknown"  # Not yet assessed


class CheckType(str, Enum):
    """Type of partner check performed."""

    HANDELSREGISTER = "handelsregister"  # Commercial register
    CREDIT_CHECK = "credit_check"  # Credit/Bonität
    SANCTIONS = "sanctions"  # Sanction list check
    NEWS = "news"  # News/media check
    INSOLVENCY = "insolvency"  # Insolvency check
    ESG = "esg"  # ESG/Sustainability check
    MANUAL = "manual"  # Manual review


class CheckStatus(str, Enum):
    """Status of a partner check."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    """Severity of partner alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Type of partner alert."""

    INSOLVENCY = "insolvency"  # Insolvency filing
    MANAGEMENT_CHANGE = "management_change"  # Geschäftsführerwechsel
    ADDRESS_CHANGE = "address_change"  # Adressänderung
    CREDIT_DOWNGRADE = "credit_downgrade"  # Bonität verschlechtert
    SANCTION_HIT = "sanction_hit"  # Auf Sanktionsliste
    NEGATIVE_NEWS = "negative_news"  # Negative Nachrichten
    LEGAL_ISSUE = "legal_issue"  # Rechtliche Probleme
    FINANCIAL_WARNING = "financial_warning"  # Finanzielle Warnung


class Partner(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Business partner entity."""

    __tablename__ = "partners"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Who created this
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Basic info (manually entered or from external source)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    partner_type: Mapped[PartnerType] = mapped_column(
        String(50), default=PartnerType.OTHER, nullable=False
    )

    # Company identifiers
    handelsregister_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # HRB 12345
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Steuernummer
    vat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # USt-IdNr

    # Address
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(
        String(2), default="DE", nullable=False
    )  # ISO 3166-1 alpha-2

    # Contact
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Risk assessment
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    risk_level: Mapped[PartnerRiskLevel] = mapped_column(
        String(50), default=PartnerRiskLevel.UNKNOWN, nullable=False
    )
    last_check_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # External data cache (from APIs)
    external_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Watchlist - if true, partner will be monitored for changes
    is_watched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="partners",
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="partners",
        foreign_keys=[created_by],
    )
    checks: Mapped[list["PartnerCheck"]] = relationship(
        "PartnerCheck",
        back_populates="partner",
        cascade="all, delete-orphan",
        order_by="desc(PartnerCheck.created_at)",
    )
    alerts: Mapped[list["PartnerAlert"]] = relationship(
        "PartnerAlert",
        back_populates="partner",
        cascade="all, delete-orphan",
        order_by="desc(PartnerAlert.created_at)",
    )
    contract_links: Mapped[list["ContractPartner"]] = relationship(
        "ContractPartner",
        back_populates="partner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Partner {self.name}>"


class PartnerCheck(Base, TenantMixin, TimestampMixin):
    """Record of a partner check (e.g., credit check, sanctions check)."""

    __tablename__ = "partner_checks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Link to partner
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Check details
    check_type: Mapped[CheckType] = mapped_column(String(50), nullable=False)
    status: Mapped[CheckStatus] = mapped_column(
        String(50), default=CheckStatus.PENDING, nullable=False
    )

    # Results
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Component score 0-100
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Provider info
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "north_data"
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    partner: Mapped["Partner"] = relationship(
        "Partner",
        back_populates="checks",
    )

    def __repr__(self) -> str:
        return f"<PartnerCheck {self.check_type} for {self.partner_id}>"


class PartnerAlert(Base, TenantMixin, TimestampMixin):
    """Alert/notification about a partner change or risk."""

    __tablename__ = "partner_alerts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Link to partner
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Alert details
    alert_type: Mapped[AlertType] = mapped_column(String(50), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Source of alert
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    dismissed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    partner: Mapped["Partner"] = relationship(
        "Partner",
        back_populates="alerts",
    )

    def __repr__(self) -> str:
        return f"<PartnerAlert {self.alert_type}: {self.title}>"


class ContractPartner(Base, TenantMixin, TimestampMixin):
    """Link between contracts and partners (many-to-many)."""

    __tablename__ = "contract_partners"
    __table_args__ = (UniqueConstraint("contract_id", "partner_id", name="uq_contract_partner"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Links
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role in contract
    role: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g., "supplier", "contractor"

    # Notes about this relationship
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="partner_links",
    )
    partner: Mapped["Partner"] = relationship(
        "Partner",
        back_populates="contract_links",
    )

    def __repr__(self) -> str:
        return f"<ContractPartner contract={self.contract_id} partner={self.partner_id}>"
