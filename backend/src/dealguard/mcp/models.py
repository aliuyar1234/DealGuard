"""Pydantic models for MCP tool input validation.

These models define the input schemas for all DealGuard MCP tools.
Using Pydantic v2 with proper validation, descriptions, and constraints.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# Enums
# ============================================================================


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"  # Human-readable, default
    JSON = "json"  # Machine-readable for programmatic processing


class LawType(str, Enum):
    """Type of Austrian legal source."""

    BUNDESRECHT = "Bundesrecht"  # Federal laws (ABGB, UGB, KSchG)
    LANDESRECHT = "Landesrecht"  # State laws
    JUSTIZ = "Justiz"  # Supreme Court (OGH) decisions
    VFGH = "Vfgh"  # Constitutional Court
    VWGH = "Vwgh"  # Administrative Court


class Bundesland(str, Enum):
    """Austrian federal states (Bundesländer)."""

    WIEN = "W"
    NIEDEROESTERREICH = "N"
    OBEROESTERREICH = "O"
    SALZBURG = "S"
    TIROL = "T"
    VORARLBERG = "V"
    KAERNTEN = "K"
    STEIERMARK = "ST"
    BURGENLAND = "B"


class RiskLevel(str, Enum):
    """Partner risk level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntityType(str, Enum):
    """Type of entity for compliance check."""

    COMPANY = "company"
    PERSON = "person"


# ============================================================================
# RIS Tools Input Models
# ============================================================================


class SearchRISInput(BaseModel):
    """Input model for searching Austrian legal database (RIS)."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search terms for legal content (e.g., 'Kündigungsfrist Mietvertrag', 'Gewährleistung Kauf', 'GmbH Haftung')",
        min_length=2,
        max_length=200,
        examples=["Kündigungsfrist ABGB", "Gewährleistung Kaufvertrag", "Geschäftsführer Haftung"],
    )
    law_type: LawType = Field(
        default=LawType.BUNDESRECHT,
        description="Type of legal source: 'Bundesrecht' for federal laws, 'Justiz' for OGH decisions, 'Vfgh'/'Vwgh' for courts",
    )
    limit: int = Field(default=5, description="Maximum number of results to return", ge=1, le=20)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for programmatic processing",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()


class GetLawTextInput(BaseModel):
    """Input model for retrieving full law text from RIS."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    document_number: str = Field(
        ...,
        description="RIS document number obtained from search_ris results (e.g., 'NOR40000001')",
        min_length=5,
        max_length=50,
        examples=["NOR40000001", "NOR12345678"],
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for programmatic processing",
    )


# ============================================================================
# Ediktsdatei Tools Input Models
# ============================================================================


class SearchEdiktsdateiInput(BaseModel):
    """Input model for searching Austrian insolvency database (Ediktsdatei)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(
        ...,
        description="Company name or person name to search for insolvency records (e.g., 'ABC GmbH', 'Muster Max')",
        min_length=2,
        max_length=200,
        examples=["ABC GmbH", "Beispiel Handels GmbH"],
    )
    bundesland: Bundesland | None = Field(
        default=None, description="Filter by Austrian federal state (optional)"
    )
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=50)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class CheckInsolvencyInput(BaseModel):
    """Input model for quick insolvency check."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    company_name: str = Field(
        ..., description="Exact or partial company name to check", min_length=2, max_length=200
    )


# ============================================================================
# Firmenbuch Tools Input Models
# ============================================================================


class SearchFirmenbuchInput(BaseModel):
    """Input model for searching Austrian company registry (Firmenbuch)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Company name or part of it (e.g., 'Red Bull', 'OMV', 'Erste Bank')",
        min_length=2,
        max_length=200,
        examples=["Red Bull", "OMV", "Erste Bank"],
    )
    limit: int = Field(default=5, description="Maximum number of results", ge=1, le=20)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class GetFirmenbuchAuszugInput(BaseModel):
    """Input model for retrieving detailed company data from Firmenbuch."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    firmenbuchnummer: str = Field(
        ...,
        description="Firmenbuch number, with or without 'FN' prefix (e.g., '123456a', 'FN 123456a')",
        min_length=3,
        max_length=20,
        examples=["123456a", "FN 123456a", "98765b"],
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )

    @field_validator("firmenbuchnummer")
    @classmethod
    def normalize_fn(cls, v: str) -> str:
        # Remove 'FN' prefix if present
        v = v.strip().upper().replace("FN", "").replace(" ", "")
        return v.lower()


class CheckCompanyAustriaInput(BaseModel):
    """Input model for quick Austrian company check."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    company_name: str = Field(
        ...,
        description="Name of the Austrian company to check",
        min_length=2,
        max_length=200,
        examples=["ABC GmbH", "Muster Handels AG"],
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


# ============================================================================
# Sanctions Tools Input Models
# ============================================================================


class CheckSanctionsInput(BaseModel):
    """Input model for sanctions list check."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(
        ...,
        description="Name of company or person to check against sanctions lists",
        min_length=2,
        max_length=200,
        examples=["Russian Export Company", "Max Mustermann"],
    )
    country: str = Field(
        default="AT",
        description="Country code for context (ISO 2-letter, e.g., 'AT', 'DE', 'RU')",
        min_length=2,
        max_length=2,
    )
    aliases: list[str] | None = Field(
        default=None, description="Alternative names to also check", max_length=5
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class CheckPEPInput(BaseModel):
    """Input model for PEP (Politically Exposed Person) check."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    person_name: str = Field(
        ...,
        description="Full name of person to check for PEP status",
        min_length=2,
        max_length=200,
        examples=["Max Mustermann", "Maria Beispiel"],
    )
    country: str = Field(
        default="AT", description="Country code for context", min_length=2, max_length=2
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class ComprehensiveComplianceInput(BaseModel):
    """Input model for comprehensive compliance check (sanctions + PEP)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(
        ...,
        description="Name of company or person for compliance screening",
        min_length=2,
        max_length=200,
    )
    entity_type: EntityType = Field(
        default=EntityType.COMPANY, description="Type of entity: 'company' or 'person'"
    )
    country: str = Field(
        default="AT", description="Country code for context", min_length=2, max_length=2
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


# ============================================================================
# DealGuard DB Tools Input Models
# ============================================================================


class SearchContractsInput(BaseModel):
    """Input model for searching user's contracts."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search terms to find in contract text (e.g., 'Kündigungsfrist', 'Zahlungsziel', 'Haftung')",
        min_length=2,
        max_length=200,
        examples=["Kündigungsfrist", "Zahlungsziel 30 Tage", "Haftungsausschluss"],
    )
    contract_type: str | None = Field(
        default=None,
        description="Filter by contract type (e.g., 'Mietvertrag', 'Kaufvertrag', 'Dienstleistung')",
    )
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=50)
    offset: int = Field(default=0, description="Number of results to skip for pagination", ge=0)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class GetContractInput(BaseModel):
    """Input model for retrieving a specific contract."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contract_id: str = Field(
        ..., description="UUID of the contract to retrieve", min_length=36, max_length=36
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class GetPartnersInput(BaseModel):
    """Input model for listing business partners."""

    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel | None = Field(
        default=None, description="Filter by risk level (optional)"
    )
    limit: int = Field(default=20, description="Maximum number of results", ge=1, le=100)
    offset: int = Field(default=0, description="Number of results to skip for pagination", ge=0)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )


class GetDeadlinesInput(BaseModel):
    """Input model for retrieving upcoming deadlines."""

    model_config = ConfigDict(extra="forbid")

    days_ahead: int = Field(
        default=30, description="How many days ahead to look for deadlines", ge=1, le=365
    )
    include_overdue: bool = Field(default=True, description="Include overdue deadlines in results")
    limit: int = Field(default=20, description="Maximum number of results", ge=1, le=100)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format"
    )
