"""Base classes for external data providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CompanySearchResult:
    """Result from company search."""

    provider_id: str  # External ID from provider
    name: str
    legal_form: str | None = None
    city: str | None = None
    country: str = "DE"
    handelsregister_id: str | None = None
    status: str | None = None  # active, liquidation, etc.
    confidence_score: float = 1.0  # 0-1 match confidence


@dataclass
class CompanyData:
    """Full company data from provider."""

    provider_id: str
    name: str
    legal_form: str | None = None
    # Registration
    handelsregister_id: str | None = None
    registration_court: str | None = None
    registration_date: str | None = None
    # Address
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str = "DE"
    # Capital
    share_capital: float | None = None
    share_capital_currency: str = "EUR"
    # Status
    status: str | None = None  # active, liquidation, dissolved
    # Management
    managing_directors: list[str] | None = None
    # Business
    business_purpose: str | None = None
    industry_codes: list[str] | None = None
    # Dates
    founded_date: str | None = None
    last_annual_report_date: str | None = None
    # Raw data
    raw_data: dict[str, Any] | None = None


@dataclass
class CreditCheckResult:
    """Result from credit/bonität check."""

    score: int  # 0-100 (0=best, 100=worst for DealGuard)
    rating: str | None = None  # e.g., "AAA", "BB"
    payment_index: int | None = None  # Days over payment terms
    credit_limit_eur: float | None = None
    insolvency_risk: str | None = None  # low, medium, high
    summary: str | None = None
    raw_data: dict[str, Any] | None = None


@dataclass
class SanctionCheckResult:
    """Result from sanctions list check."""

    is_sanctioned: bool
    matches: list[dict[str, Any]] | None = None  # Matching entries
    lists_checked: list[str] | None = None  # Which lists were searched
    score: int = 0  # 0 = clean, 100 = sanctioned
    summary: str | None = None
    raw_data: dict[str, Any] | None = None


@dataclass
class InsolvencyCheckResult:
    """Result from insolvency check."""

    has_proceedings: bool
    proceedings: list[dict[str, Any]] | None = None
    score: int = 0  # 0 = no proceedings, 100 = active insolvency
    summary: str | None = None
    raw_data: dict[str, Any] | None = None


class CompanyDataProvider(ABC):
    """Base class for company data providers (e.g., North Data, CompanyHub)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging/reference."""
        pass

    @abstractmethod
    async def search_companies(
        self,
        query: str,
        country: str = "DE",
        limit: int = 10,
    ) -> list[CompanySearchResult]:
        """Search for companies by name.

        Args:
            query: Company name to search for
            country: ISO country code (DE, AT, CH)
            limit: Maximum results to return

        Returns:
            List of matching companies
        """
        pass

    @abstractmethod
    async def get_company_data(
        self,
        provider_id: str,
    ) -> CompanyData | None:
        """Get full company data by provider ID.

        Args:
            provider_id: External ID from provider

        Returns:
            Company data or None if not found
        """
        pass

    async def get_company_by_register_id(
        self,
        register_id: str,
        court: str | None = None,
    ) -> CompanyData | None:
        """Get company by Handelsregister ID.

        Args:
            register_id: Handelsregister number (e.g., "HRB 12345")
            court: Optional registration court

        Returns:
            Company data or None if not found
        """
        # Default implementation: search and match
        results = await self.search_companies(register_id, limit=5)
        for r in results:
            if r.handelsregister_id != register_id:
                continue

            company = await self.get_company_data(r.provider_id)
            if (
                company
                and court
                and company.registration_court
                and company.registration_court != court
            ):
                continue

            return company
        return None


class CreditProvider(ABC):
    """Base class for credit/bonität providers (e.g., Creditreform, SCHUFA B2B)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    async def check_credit(
        self,
        company_name: str,
        handelsregister_id: str | None = None,
        address: str | None = None,
    ) -> CreditCheckResult:
        """Perform credit check on a company.

        Args:
            company_name: Company name
            handelsregister_id: Optional HR ID for precise matching
            address: Optional address for matching

        Returns:
            Credit check results
        """
        pass


class SanctionProvider(ABC):
    """Base class for sanctions list providers (e.g., OpenSanctions)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    async def check_sanctions(
        self,
        company_name: str,
        country: str = "DE",
        aliases: list[str] | None = None,
    ) -> SanctionCheckResult:
        """Check if company is on sanctions lists.

        Args:
            company_name: Company name to check
            country: Country for context
            aliases: Alternative names to also check

        Returns:
            Sanction check results
        """
        pass


class InsolvencyProvider(ABC):
    """Base class for insolvency check providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    async def check_insolvency(
        self,
        company_name: str,
        handelsregister_id: str | None = None,
    ) -> InsolvencyCheckResult:
        """Check for insolvency proceedings.

        Args:
            company_name: Company name
            handelsregister_id: Optional HR ID

        Returns:
            Insolvency check results
        """
        pass
