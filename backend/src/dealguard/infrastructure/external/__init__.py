"""External data providers for partner intelligence."""

from dealguard.infrastructure.external.base import (
    CompanyDataProvider,
    CompanySearchResult,
    CompanyData,
    CreditProvider,
    CreditCheckResult,
    SanctionProvider,
    SanctionCheckResult,
    InsolvencyProvider,
    InsolvencyCheckResult,
)
from dealguard.infrastructure.external.mock_provider import (
    MockCompanyProvider,
    MockCreditProvider,
    MockSanctionProvider,
    MockInsolvencyProvider,
)
from dealguard.infrastructure.external.openfirmenbuch import (
    OpenFirmenbuchProvider,
    FallbackFirmenbuchProvider,
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
