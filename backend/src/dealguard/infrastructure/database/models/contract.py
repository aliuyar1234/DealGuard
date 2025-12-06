"""Contract and analysis models."""

import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealguard.infrastructure.database.models.base import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dealguard.infrastructure.database.models.organization import Organization
    from dealguard.infrastructure.database.models.user import User
    from dealguard.infrastructure.database.models.partner import ContractPartner


class ContractType(str, Enum):
    """Types of contracts we can analyze."""

    SUPPLIER = "supplier"  # Lieferantenvertrag
    CUSTOMER = "customer"  # Kundenvertrag / AGB
    SERVICE = "service"  # Dienstleistungsvertrag
    NDA = "nda"  # Geheimhaltungsvereinbarung
    LEASE = "lease"  # Mietvertrag (Gewerbe)
    EMPLOYMENT = "employment"  # Arbeitsvertrag
    LICENSE = "license"  # Lizenzvertrag
    OTHER = "other"  # Sonstige


class AnalysisStatus(str, Enum):
    """Status of contract analysis."""

    PENDING = "pending"  # Queued for processing
    PROCESSING = "processing"  # Currently being analyzed
    COMPLETED = "completed"  # Analysis finished
    FAILED = "failed"  # Analysis failed


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"  # 0-30
    MEDIUM = "medium"  # 31-60
    HIGH = "high"  # 61-80
    CRITICAL = "critical"  # 81-100


class FindingSeverity(str, Enum):
    """Severity of a finding."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(str, Enum):
    """Category of contract findings."""

    LIABILITY = "liability"  # Haftung
    PAYMENT = "payment"  # Zahlungsbedingungen
    TERMINATION = "termination"  # Kündigung
    JURISDICTION = "jurisdiction"  # Gerichtsstand
    IP = "ip"  # Geistiges Eigentum
    CONFIDENTIALITY = "confidentiality"  # Geheimhaltung
    GDPR = "gdpr"  # Datenschutz
    WARRANTY = "warranty"  # Gewährleistung
    FORCE_MAJEURE = "force_majeure"  # Höhere Gewalt
    OTHER = "other"


class Contract(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Contract document."""

    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Who created this
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # S3 key
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Contract info
    contract_type: Mapped[ContractType | None] = mapped_column(
        String(50), nullable=True
    )
    language: Mapped[str] = mapped_column(String(10), default="de", nullable=False)

    # Analysis status
    status: Mapped[AnalysisStatus] = mapped_column(
        String(50),
        default=AnalysisStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted text (stored encrypted, access via contract_text property)
    _raw_text_encrypted: Mapped[str | None] = mapped_column(
        "raw_text", Text, nullable=True
    )

    @hybrid_property
    def contract_text(self) -> str | None:
        """Get decrypted contract text.

        Automatically decrypts text stored in the database.
        Returns None if no text or decryption fails.
        """
        if not self._raw_text_encrypted:
            return None

        try:
            from dealguard.shared.crypto import decrypt_secret, is_encrypted

            if is_encrypted(self._raw_text_encrypted):
                return decrypt_secret(self._raw_text_encrypted)
            # Legacy: unencrypted text (backwards compatibility)
            return self._raw_text_encrypted
        except Exception as e:
            logger.error(f"Failed to decrypt contract text: {e}")
            return None

    @contract_text.setter
    def contract_text(self, value: str | None) -> None:
        """Set contract text with automatic encryption.

        Encrypts text before storing in database.
        """
        if not value:
            self._raw_text_encrypted = None
            return

        try:
            from dealguard.shared.crypto import encrypt_secret

            self._raw_text_encrypted = encrypt_secret(value)
        except Exception as e:
            logger.error(f"Failed to encrypt contract text: {e}")
            # Store unencrypted as fallback (dev mode)
            self._raw_text_encrypted = value

    # Legacy property for backwards compatibility
    @property
    def raw_text(self) -> str | None:
        """Deprecated: Use contract_text instead."""
        return self.contract_text

    @raw_text.setter
    def raw_text(self, value: str | None) -> None:
        """Deprecated: Use contract_text instead."""
        self.contract_text = value

    # Contract metadata (additional info)
    contract_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="contracts",
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="contracts",
        foreign_keys=[created_by],
    )
    analysis: Mapped["ContractAnalysis | None"] = relationship(
        "ContractAnalysis",
        back_populates="contract",
        uselist=False,
        cascade="all, delete-orphan",
    )
    partner_links: Mapped[list["ContractPartner"]] = relationship(
        "ContractPartner",
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Contract {self.filename}>"


class ContractAnalysis(Base, TenantMixin, TimestampMixin):
    """Analysis results for a contract."""

    __tablename__ = "contract_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # One-to-one with Contract
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Results
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    risk_level: Mapped[RiskLevel] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Processing metadata
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Cost tracking
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_cents: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    contract: Mapped["Contract"] = relationship(
        "Contract",
        back_populates="analysis",
    )
    findings: Mapped[list["ContractFinding"]] = relationship(
        "ContractFinding",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="desc(ContractFinding.severity)",
    )

    def __repr__(self) -> str:
        return f"<ContractAnalysis score={self.risk_score}>"


class ContractFinding(Base, TenantMixin, TimestampMixin):
    """Individual finding from contract analysis."""

    __tablename__ = "contract_findings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Belongs to analysis
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("contract_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Finding details
    category: Mapped[FindingCategory] = mapped_column(String(50), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Original clause
    original_clause_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    clause_location: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {page, paragraph}

    # Recommendations
    suggested_change: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_comparison: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    analysis: Mapped["ContractAnalysis"] = relationship(
        "ContractAnalysis",
        back_populates="findings",
    )

    def __repr__(self) -> str:
        return f"<ContractFinding {self.category}: {self.title}>"
