"""Proactive AI-Jurist system models.

These models enable the proactive monitoring features:
- ContractDeadline: Extracted dates/deadlines from contracts
- ProactiveAlert: AI-generated alerts with recommended actions
- ComplianceCheck: Periodic compliance scan results
- RiskSnapshot: Daily risk score snapshots for trending
"""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Integer, Float, Date, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealguard.infrastructure.database.models.base import (
    Base,
    TenantMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from dealguard.infrastructure.database.models.organization import Organization
    from dealguard.infrastructure.database.models.contract import Contract
    from dealguard.infrastructure.database.models.partner import Partner
    from dealguard.infrastructure.database.models.user import User


# ─────────────────────────────────────────────────────────────
#                         ENUMS
# ─────────────────────────────────────────────────────────────


class DeadlineType(str, Enum):
    """Types of contract deadlines."""

    TERMINATION_NOTICE = "termination_notice"  # Kündigungsfrist
    AUTO_RENEWAL = "auto_renewal"  # Automatische Verlängerung
    PAYMENT_DUE = "payment_due"  # Zahlungsfrist
    WARRANTY_END = "warranty_end"  # Gewährleistungsende
    CONTRACT_END = "contract_end"  # Vertragsende
    REVIEW_DATE = "review_date"  # Überprüfungsdatum
    PRICE_ADJUSTMENT = "price_adjustment"  # Preisanpassung
    NOTICE_PERIOD = "notice_period"  # Ankündigungsfrist
    OTHER = "other"


class DeadlineStatus(str, Enum):
    """Status of a deadline."""

    ACTIVE = "active"  # Upcoming, needs attention
    HANDLED = "handled"  # User took action
    EXPIRED = "expired"  # Deadline passed without action
    DISMISSED = "dismissed"  # User dismissed it


class AlertSourceType(str, Enum):
    """What triggered the alert."""

    DEADLINE = "deadline"
    PARTNER_RISK = "partner_risk"
    COMPLIANCE = "compliance"
    OPPORTUNITY = "opportunity"
    CONTRACT_RISK = "contract_risk"
    MARKET_CHANGE = "market_change"


class AlertType(str, Enum):
    """Types of proactive alerts."""

    DEADLINE_APPROACHING = "deadline_approaching"
    AUTO_RENEWAL_WARNING = "auto_renewal_warning"
    PARTNER_RISK_CHANGE = "partner_risk_change"
    PARTNER_INSOLVENCY = "partner_insolvency"
    COMPLIANCE_ISSUE = "compliance_issue"
    CONTRACT_RISK = "contract_risk"
    OPPORTUNITY = "opportunity"
    PAYMENT_DUE = "payment_due"
    PRICE_INCREASE = "price_increase"
    BETTER_TERMS_AVAILABLE = "better_terms_available"


class AlertSeverity(str, Enum):
    """Severity of an alert."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Status of an alert."""

    NEW = "new"
    SEEN = "seen"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"


class ComplianceCheckType(str, Enum):
    """Types of compliance checks."""

    GDPR = "gdpr"  # Datenschutz
    AVV = "avv"  # Auftragsverarbeitungsvertrag
    LIABILITY_CAP = "liability_cap"  # Haftungsbeschränkung
    PAYMENT_TERMS = "payment_terms"  # Zahlungsbedingungen
    TERMINATION_CLAUSE = "termination_clause"  # Kündigungsklausel
    JURISDICTION = "jurisdiction"  # Gerichtsstand
    IP_RIGHTS = "ip_rights"  # Geistiges Eigentum
    CONFIDENTIALITY = "confidentiality"  # Geheimhaltung
    WARRANTY = "warranty"  # Gewährleistung
    FORCE_MAJEURE = "force_majeure"  # Höhere Gewalt


class ComplianceStatus(str, Enum):
    """Status of a compliance check."""

    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"


# ─────────────────────────────────────────────────────────────
#                         MODELS
# ─────────────────────────────────────────────────────────────


class ContractDeadline(Base, TenantMixin, TimestampMixin):
    """An extracted deadline from a contract.

    AI analyzes contracts and extracts important dates:
    - Kündigungsfristen
    - Automatische Verlängerungen
    - Zahlungsziele
    - Gewährleistungsfristen
    - etc.
    """

    __tablename__ = "contract_deadlines"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Which contract
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Deadline info
    deadline_type: Mapped[DeadlineType] = mapped_column(String(50), nullable=False)
    deadline_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reminder_days_before: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Source clause (for transparency)
    source_clause: Mapped[str | None] = mapped_column(Text, nullable=True)
    clause_location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # AI extraction metadata
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    extracted_by_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status
    status: Mapped[DeadlineStatus] = mapped_column(
        String(50), default=DeadlineStatus.ACTIVE, nullable=False, index=True
    )
    handled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    handled_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    handled_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contract: Mapped["Contract"] = relationship("Contract", backref="deadlines")
    handled_by_user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ContractDeadline {self.deadline_type}: {self.deadline_date}>"

    @property
    def days_until(self) -> int:
        """Days until this deadline."""
        return (self.deadline_date - date.today()).days

    @property
    def is_overdue(self) -> bool:
        """Check if deadline has passed."""
        return self.deadline_date < date.today()

    @property
    def needs_attention(self) -> bool:
        """Check if deadline needs attention (within reminder period)."""
        return self.days_until <= self.reminder_days_before and not self.is_overdue


class ProactiveAlert(Base, TenantMixin, TimestampMixin):
    """A proactive alert generated by the AI-Jurist.

    Alerts are generated when:
    - Deadlines are approaching
    - Partner risk changes significantly
    - Compliance issues are detected
    - Opportunities are identified
    """

    __tablename__ = "proactive_alerts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Source (what triggered this)
    source_type: Mapped[AlertSourceType] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(nullable=True)

    # Alert content
    alert_type: Mapped[AlertType] = mapped_column(String(50), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        String(20), default=AlertSeverity.MEDIUM, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # AI recommendation
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [{"action": "terminate", "label": "Kündigen", "params": {...}}, ...]

    # Related entities
    related_contract_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True
    )
    related_partner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True
    )

    # Status
    status: Mapped[AlertStatus] = mapped_column(
        String(50), default=AlertStatus.NEW, nullable=False, index=True
    )
    snoozed_until: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When action is needed by
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # Relationships
    related_contract: Mapped["Contract | None"] = relationship("Contract")
    related_partner: Mapped["Partner | None"] = relationship("Partner")
    resolved_by_user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ProactiveAlert {self.alert_type}: {self.title[:30]}>"

    @property
    def is_actionable(self) -> bool:
        """Check if alert can still be acted upon."""
        return self.status in (AlertStatus.NEW, AlertStatus.SEEN, AlertStatus.IN_PROGRESS)


class ComplianceCheck(Base, TenantMixin):
    """A compliance check result for a contract.

    The system periodically scans contracts for compliance issues:
    - DSGVO / GDPR
    - AVV (Auftragsverarbeitung)
    - Unfaire Klauseln
    - etc.
    """

    __tablename__ = "compliance_checks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Check info
    check_type: Mapped[ComplianceCheckType] = mapped_column(String(50), nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(
        String(20), default=AlertSeverity.MEDIUM, nullable=False
    )

    # Finding details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_clause: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_change: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    checked_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    ai_model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Resolution
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    contract: Mapped["Contract"] = relationship("Contract", backref="compliance_checks")
    resolved_by_user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ComplianceCheck {self.check_type}: {self.status}>"


class RiskSnapshot(Base, TenantMixin):
    """Daily snapshot of organization risk scores.

    Used for:
    - Risk trending over time
    - Dashboard visualizations
    - Early warning detection
    """

    __tablename__ = "risk_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Aggregate scores (0-100)
    overall_risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    partner_risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    compliance_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Counts
    total_contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    high_risk_contracts: Mapped[int] = mapped_column(Integer, nullable=False)
    total_partners: Mapped[int] = mapped_column(Integer, nullable=False)
    high_risk_partners: Mapped[int] = mapped_column(Integer, nullable=False)
    pending_deadlines: Mapped[int] = mapped_column(Integer, nullable=False)
    open_alerts: Mapped[int] = mapped_column(Integer, nullable=False)

    # Detailed breakdown
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RiskSnapshot {self.snapshot_date}: {self.overall_risk_score}>"
