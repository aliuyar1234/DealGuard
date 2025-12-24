"""External data providers for partner intelligence."""

from dealguard.infrastructure.external.base import (
    CompanyData,
    CompanyDataProvider,
    CompanySearchResult,
    CreditCheckResult,
    CreditProvider,
    InsolvencyCheckResult,
    InsolvencyProvider,
    SanctionCheckResult,
    SanctionProvider,
)
from dealguard.infrastructure.external.mock_provider import (
    MockCompanyProvider,
    MockCreditProvider,
    MockInsolvencyProvider,
    MockSanctionProvider,
)
from dealguard.infrastructure.external.openfirmenbuch import (
    FallbackFirmenbuchProvider,
    OpenFirmenbuchProvider,
)
from dealguard.infrastructure.external.opensanctions import (
    OpenSanctionsProvider,
    PEPScreeningProvider,
)

__all__ = [
    # Base classes
    "CompanyDataProvider",
    "CompanySearchResult",
    "CompanyData",
    "CreditProvider",
    "CreditCheckResult",
    "SanctionProvider",
    "SanctionCheckResult",
    "InsolvencyProvider",
    "InsolvencyCheckResult",
    # Mock providers (for testing)
    "MockCompanyProvider",
    "MockCreditProvider",
    "MockSanctionProvider",
    "MockInsolvencyProvider",
    # Real providers
    "OpenFirmenbuchProvider",
    "FallbackFirmenbuchProvider",
    "OpenSanctionsProvider",
    "PEPScreeningProvider",
]
