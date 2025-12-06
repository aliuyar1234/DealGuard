"""OpenFirmenbuch client for free Austrian company data.

OpenFirmenbuch (by WhizUs) provides free access to Austrian Firmenbuch data.
Source: https://github.com/openfirmenbuch/openfirmenbuch

This is a completely free alternative to paid services like North Data.
Data is extracted from official Austrian Firmenbuch announcements.
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from dealguard.infrastructure.external.base import (
    CompanyDataProvider,
    CompanySearchResult,
    CompanyData,
)

logger = logging.getLogger(__name__)

# OpenFirmenbuch API endpoints (hosted by WhizUs)
# Note: This API provides historical data from Austrian Firmenbuch
OPENFIRMENBUCH_BASE_URL = "https://openfirmenbuch.at/api/v1"


class OpenFirmenbuchProvider(CompanyDataProvider):
    """Austrian company data provider using OpenFirmenbuch (free).

    OpenFirmenbuch provides:
    - Company names (Firmenwortlaut)
    - Firmenbuchnummer (FN)
    - Legal form
    - Registered office (Sitz)
    - Managing directors (Geschäftsführer)
    - Capital information

    Limitations:
    - Only Austrian companies
    - Data may not be real-time (periodic updates)
    - No detailed financial data or ratings
    """

    def __init__(self, timeout: float = 30.0):
        """Initialize the OpenFirmenbuch client.

        Args:
            timeout: Request timeout in seconds
        """
        self.base_url = OPENFIRMENBUCH_BASE_URL
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "openfirmenbuch"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "DealGuard/2.0 (https://github.com/dealguard)",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_companies(
        self,
        query: str,
        country: str = "AT",
        limit: int = 10,
    ) -> list[CompanySearchResult]:
        """Search for Austrian companies by name.

        Args:
            query: Company name to search for
            country: Country code (only AT supported)
            limit: Maximum results to return

        Returns:
            List of matching companies
        """
        if country != "AT":
            logger.warning(f"OpenFirmenbuch only supports AT, got {country}")
            return []

        try:
            client = await self._get_client()

            # OpenFirmenbuch uses simple text search
            response = await client.get(
                f"{self.base_url}/companies",
                params={
                    "q": query,
                    "limit": limit,
                },
            )

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            results = []
            for company in data.get("companies", data if isinstance(data, list) else []):
                results.append(
                    CompanySearchResult(
                        provider_id=company.get("fn", company.get("id", "")),
                        name=company.get("name", company.get("firmenwortlaut", "")),
                        legal_form=self._extract_legal_form(company.get("name", "")),
                        city=company.get("sitz", company.get("city", "")),
                        country="AT",
                        handelsregister_id=company.get("fn", ""),  # Firmenbuchnummer
                        status=company.get("status", "active"),
                        confidence_score=1.0,
                    )
                )

            return results[:limit]

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenFirmenbuch API error: {e}")
            return []
        except httpx.RequestError as e:
            logger.error(f"OpenFirmenbuch request error: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error in OpenFirmenbuch search: {e}")
            return []

    async def get_company_data(
        self,
        provider_id: str,
    ) -> CompanyData | None:
        """Get full company data by Firmenbuchnummer.

        Args:
            provider_id: Firmenbuchnummer (e.g., "123456a")

        Returns:
            Company data or None if not found
        """
        try:
            client = await self._get_client()

            # Normalize FN (remove spaces, lowercase)
            fn = provider_id.strip().lower().replace(" ", "")

            response = await client.get(f"{self.base_url}/companies/{fn}")

            if response.status_code == 404:
                return None

            response.raise_for_status()
            company = response.json()

            return CompanyData(
                provider_id=fn,
                name=company.get("name", company.get("firmenwortlaut", "")),
                legal_form=self._extract_legal_form(company.get("name", "")),
                # Registration
                handelsregister_id=company.get("fn", fn),
                registration_court=company.get("firmenbuchgericht", "Handelsgericht Wien"),
                registration_date=company.get("eintragungsdatum"),
                # Address
                street=company.get("adresse", {}).get("strasse") if isinstance(company.get("adresse"), dict) else None,
                postal_code=company.get("adresse", {}).get("plz") if isinstance(company.get("adresse"), dict) else None,
                city=company.get("sitz", company.get("adresse", {}).get("ort") if isinstance(company.get("adresse"), dict) else None),
                country="AT",
                # Capital
                share_capital=self._parse_capital(company.get("stammkapital")),
                share_capital_currency="EUR",
                # Status
                status=company.get("status", "active"),
                # Management
                managing_directors=company.get("geschaeftsfuehrer", []),
                # Business
                business_purpose=company.get("unternehmensgegenstand"),
                industry_codes=None,  # Not provided by OpenFirmenbuch
                # Dates
                founded_date=company.get("gruendungsdatum"),
                last_annual_report_date=None,
                # Raw data
                raw_data=company,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenFirmenbuch API error: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"OpenFirmenbuch request error: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting company data: {e}")
            return None

    async def search_by_fn(self, fn: str) -> CompanyData | None:
        """Search company by Firmenbuchnummer (convenience method).

        Args:
            fn: Firmenbuchnummer (e.g., "FN 123456a", "123456a")

        Returns:
            Company data or None
        """
        # Clean up FN format
        fn_clean = fn.upper().replace("FN", "").replace(" ", "").strip().lower()
        return await self.get_company_data(fn_clean)

    def _extract_legal_form(self, name: str) -> str | None:
        """Extract legal form from company name."""
        legal_forms = [
            "GmbH",
            "AG",
            "KG",
            "OG",
            "e.U.",
            "GesbR",
            "GmbH & Co KG",
            "Privatstiftung",
            "Verein",
            "Gen",  # Genossenschaft
        ]

        for form in legal_forms:
            if form.lower() in name.lower():
                return form

        return None

    def _parse_capital(self, capital_str: str | None) -> float | None:
        """Parse capital string to float."""
        if not capital_str:
            return None

        try:
            # Remove currency symbols and whitespace
            cleaned = capital_str.replace("EUR", "").replace("€", "").replace(",", ".").strip()
            # Remove thousands separators (in German format: 1.000.000,00 -> 1000000.00)
            parts = cleaned.split(".")
            if len(parts) > 2:
                # German format with thousands separators
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
            return float(cleaned)
        except (ValueError, AttributeError):
            return None


class FallbackFirmenbuchProvider(CompanyDataProvider):
    """Fallback provider that tries multiple free Austrian company data sources.

    Order of attempts:
    1. OpenFirmenbuch (openfirmenbuch.at)
    2. opendata.host (if API key provided)
    3. Return mock data as last resort
    """

    def __init__(
        self,
        opendata_api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.openfirmenbuch = OpenFirmenbuchProvider(timeout=timeout)
        self.opendata_api_key = opendata_api_key
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "fallback_firmenbuch"

    async def search_companies(
        self,
        query: str,
        country: str = "AT",
        limit: int = 10,
    ) -> list[CompanySearchResult]:
        """Search using fallback chain."""
        # Try OpenFirmenbuch first
        results = await self.openfirmenbuch.search_companies(query, country, limit)
        if results:
            return results

        # Try opendata.host if API key is configured
        if self.opendata_api_key:
            opendata_results = await self._search_opendata_host(query, limit)
            if opendata_results:
                return opendata_results

        logger.warning(f"No results found for '{query}' in any source")
        return []

    async def get_company_data(
        self,
        provider_id: str,
    ) -> CompanyData | None:
        """Get company data using fallback chain."""
        # Try OpenFirmenbuch
        data = await self.openfirmenbuch.get_company_data(provider_id)
        if data:
            return data

        # Try opendata.host if API key is configured
        if self.opendata_api_key:
            opendata_data = await self._get_opendata_host(provider_id)
            if opendata_data:
                return opendata_data

        return None

    async def _search_opendata_host(
        self,
        query: str,
        limit: int,
    ) -> list[CompanySearchResult]:
        """Search companies via opendata.host API."""
        if not self.opendata_api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.opendata.host/firmenbuch/search",
                    params={"q": query, "limit": limit},
                    headers={"Authorization": f"Bearer {self.opendata_api_key}"},
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                results = []

                for company in data.get("results", []):
                    results.append(
                        CompanySearchResult(
                            provider_id=company.get("fn", ""),
                            name=company.get("name", ""),
                            legal_form=company.get("rechtsform"),
                            city=company.get("sitz"),
                            country="AT",
                            handelsregister_id=company.get("fn"),
                            status="active",
                            confidence_score=company.get("score", 1.0),
                        )
                    )

                return results

        except Exception as e:
            logger.error(f"opendata.host search error: {e}")
            return []

    async def _get_opendata_host(self, fn: str) -> CompanyData | None:
        """Get company data from opendata.host."""
        if not self.opendata_api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"https://api.opendata.host/firmenbuch/{fn}",
                    headers={"Authorization": f"Bearer {self.opendata_api_key}"},
                )

                if response.status_code != 200:
                    return None

                company = response.json()

                return CompanyData(
                    provider_id=company.get("fn", fn),
                    name=company.get("name", ""),
                    legal_form=company.get("rechtsform"),
                    handelsregister_id=company.get("fn"),
                    registration_court=company.get("gericht"),
                    city=company.get("sitz"),
                    country="AT",
                    share_capital=company.get("stammkapital"),
                    managing_directors=company.get("vertretung", []),
                    business_purpose=company.get("gegenstand"),
                    raw_data=company,
                )

        except Exception as e:
            logger.error(f"opendata.host get error: {e}")
            return None

    async def close(self) -> None:
        """Close all clients."""
        await self.openfirmenbuch.close()
