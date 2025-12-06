"""Mock provider for development and testing."""

import random
from datetime import datetime, timedelta

from dealguard.infrastructure.external.base import (
    CompanyDataProvider,
    CreditProvider,
    SanctionProvider,
    InsolvencyProvider,
    CompanySearchResult,
    CompanyData,
    CreditCheckResult,
    SanctionCheckResult,
    InsolvencyCheckResult,
)


class MockCompanyProvider(CompanyDataProvider):
    """Mock company data provider for development."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def search_companies(
        self,
        query: str,
        country: str = "DE",
        limit: int = 10,
    ) -> list[CompanySearchResult]:
        """Return mock search results."""
        # Generate mock results based on query
        mock_companies = [
            CompanySearchResult(
                provider_id=f"mock_{query.lower().replace(' ', '_')}_{i}",
                name=f"{query} {suffix}",
                legal_form=random.choice(["GmbH", "AG", "UG", "GmbH & Co. KG"]),
                city=random.choice(["Berlin", "München", "Hamburg", "Frankfurt", "Köln"]),
                country=country,
                handelsregister_id=f"HRB {random.randint(10000, 99999)}",
                status="active",
                confidence_score=0.95 - (i * 0.1),
            )
            for i, suffix in enumerate(["GmbH", "AG", "Holding", "Solutions", "Services"][:limit])
        ]
        return mock_companies

    async def get_company_data(
        self,
        provider_id: str,
    ) -> CompanyData | None:
        """Return mock company data."""
        base_name = provider_id.replace("mock_", "").replace("_", " ").title()

        return CompanyData(
            provider_id=provider_id,
            name=f"{base_name} GmbH",
            legal_form="GmbH",
            handelsregister_id=f"HRB {random.randint(10000, 99999)}",
            registration_court="Amtsgericht Berlin Charlottenburg",
            registration_date="2015-03-15",
            street="Musterstraße 123",
            postal_code="10115",
            city="Berlin",
            country="DE",
            share_capital=25000.00,
            share_capital_currency="EUR",
            status="active",
            managing_directors=["Max Mustermann", "Erika Musterfrau"],
            business_purpose="IT-Dienstleistungen und Softwareentwicklung",
            industry_codes=["62.01", "62.02"],
            founded_date="2015-03-01",
            last_annual_report_date="2023-12-31",
            raw_data={"mock": True, "generated_at": datetime.now().isoformat()},
        )


class MockCreditProvider(CreditProvider):
    """Mock credit provider for development."""

    @property
    def provider_name(self) -> str:
        return "mock_credit"

    async def check_credit(
        self,
        company_name: str,
        handelsregister_id: str | None = None,
        address: str | None = None,
    ) -> CreditCheckResult:
        """Return mock credit check results."""
        # Generate semi-random but consistent score based on company name
        name_hash = sum(ord(c) for c in company_name) % 100
        score = max(10, min(80, name_hash))

        ratings = {
            (0, 20): "AAA",
            (21, 35): "AA",
            (36, 50): "A",
            (51, 65): "BBB",
            (66, 80): "BB",
            (81, 100): "C",
        }
        rating = next(
            (r for (low, high), r in ratings.items() if low <= score <= high),
            "B"
        )

        return CreditCheckResult(
            score=score,
            rating=rating,
            payment_index=random.randint(-5, 30),
            credit_limit_eur=random.choice([50000, 100000, 250000, 500000]),
            insolvency_risk="low" if score < 40 else ("medium" if score < 70 else "high"),
            summary=f"Bonität: {rating}. {'Gute' if score < 40 else 'Durchschnittliche' if score < 70 else 'Erhöhte'} Zahlungsmoral.",
            raw_data={"mock": True, "generated_at": datetime.now().isoformat()},
        )


class MockSanctionProvider(SanctionProvider):
    """Mock sanctions provider for development."""

    @property
    def provider_name(self) -> str:
        return "mock_sanctions"

    async def check_sanctions(
        self,
        company_name: str,
        country: str = "DE",
        aliases: list[str] | None = None,
    ) -> SanctionCheckResult:
        """Return mock sanction check results - always clean."""
        return SanctionCheckResult(
            is_sanctioned=False,
            matches=None,
            lists_checked=["EU Sanctions", "UN Sanctions", "OFAC SDN"],
            score=0,
            summary="Keine Treffer auf Sanktionslisten gefunden.",
            raw_data={"mock": True, "generated_at": datetime.now().isoformat()},
        )


class MockInsolvencyProvider(InsolvencyProvider):
    """Mock insolvency provider for development."""

    @property
    def provider_name(self) -> str:
        return "mock_insolvency"

    async def check_insolvency(
        self,
        company_name: str,
        handelsregister_id: str | None = None,
    ) -> InsolvencyCheckResult:
        """Return mock insolvency check results."""
        # 95% chance of no insolvency
        has_proceedings = random.random() < 0.05

        if has_proceedings:
            return InsolvencyCheckResult(
                has_proceedings=True,
                proceedings=[
                    {
                        "type": "Regelinsolvenz",
                        "court": "Amtsgericht Berlin",
                        "date": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                        "status": "eröffnet",
                    }
                ],
                score=100,
                summary="WARNUNG: Laufendes Insolvenzverfahren!",
                raw_data={"mock": True},
            )

        return InsolvencyCheckResult(
            has_proceedings=False,
            proceedings=None,
            score=0,
            summary="Keine Insolvenzverfahren gefunden.",
            raw_data={"mock": True, "generated_at": datetime.now().isoformat()},
        )
