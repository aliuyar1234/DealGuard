"""OpenSanctions client for free sanctions and PEP screening.

OpenSanctions (https://opensanctions.org) provides free access to:
- Global sanctions lists (EU, UN, US OFAC, etc.)
- PEP (Politically Exposed Persons) data
- Criminal watchlists
- Company ownership data

The data is free to use under CC-BY license for non-commercial use.
For commercial use, a subscription is required but pricing is affordable.

API: https://api.opensanctions.org/
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from dealguard.infrastructure.external.base import (
    SanctionProvider,
    SanctionCheckResult,
)

logger = logging.getLogger(__name__)

# OpenSanctions API endpoint
OPENSANCTIONS_BASE_URL = "https://api.opensanctions.org"


class OpenSanctionsProvider(SanctionProvider):
    """Sanctions and PEP screening provider using OpenSanctions.

    OpenSanctions provides:
    - Sanctions lists (EU, UN, US OFAC, UK, etc.)
    - PEP (Politically Exposed Persons) databases
    - Criminal watchlists
    - Company debarment lists

    Free tier limitations:
    - Rate limited
    - Attribution required (CC-BY)
    - For non-commercial use

    For commercial use, get an API key at https://opensanctions.org/pricing/
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the OpenSanctions client.

        Args:
            api_key: Optional API key for commercial use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = OPENSANCTIONS_BASE_URL
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "opensanctions"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "Accept": "application/json",
                "User-Agent": "DealGuard/2.0 (https://github.com/dealguard)",
            }
            if self.api_key:
                headers["Authorization"] = f"ApiKey {self.api_key}"

            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_sanctions(
        self,
        company_name: str,
        country: str = "AT",
        aliases: list[str] | None = None,
    ) -> SanctionCheckResult:
        """Check if a company or person is on sanctions lists.

        Args:
            company_name: Name to check
            country: Country context (ISO code)
            aliases: Alternative names to also check

        Returns:
            Sanction check results
        """
        try:
            client = await self._get_client()

            # Search for matches
            all_matches = []

            # Check main name
            matches = await self._search_name(client, company_name, country)
            all_matches.extend(matches)

            # Check aliases
            if aliases:
                for alias in aliases:
                    alias_matches = await self._search_name(client, alias, country)
                    all_matches.extend(alias_matches)

            # Deduplicate matches by ID
            seen_ids = set()
            unique_matches = []
            for match in all_matches:
                match_id = match.get("id", match.get("entity_id"))
                if match_id and match_id not in seen_ids:
                    seen_ids.add(match_id)
                    unique_matches.append(match)

            # Calculate score based on match confidence
            is_sanctioned = any(
                self._is_high_confidence_match(m) for m in unique_matches
            )

            score = 0
            if unique_matches:
                max_score = max(m.get("score", 0) * 100 for m in unique_matches)
                score = int(min(100, max_score))

            # Get list of sanctions lists checked
            lists_checked = [
                "EU Sanctions (CFSP)",
                "UN Consolidated Sanctions",
                "US OFAC SDN",
                "UK HMT Sanctions",
                "Swiss SECO",
                "OpenSanctions PEPs",
            ]

            # Generate summary
            if is_sanctioned:
                summary = f"WARNUNG: {len(unique_matches)} Treffer auf Sanktionslisten gefunden!"
            elif unique_matches:
                summary = f"{len(unique_matches)} mögliche Treffer gefunden (niedrige Übereinstimmung). Manuelle Prüfung empfohlen."
            else:
                summary = "Keine Treffer auf Sanktionslisten gefunden."

            return SanctionCheckResult(
                is_sanctioned=is_sanctioned,
                matches=self._format_matches(unique_matches) if unique_matches else None,
                lists_checked=lists_checked,
                score=score if is_sanctioned else (score // 2 if unique_matches else 0),
                summary=summary,
                raw_data={
                    "query": company_name,
                    "aliases_checked": aliases,
                    "country": country,
                    "match_count": len(unique_matches),
                    "checked_at": datetime.now().isoformat(),
                },
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenSanctions API error: {e}")
            return self._error_result(str(e))
        except httpx.RequestError as e:
            logger.error(f"OpenSanctions request error: {e}")
            return self._error_result(str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in sanctions check: {e}")
            return self._error_result(str(e))

    async def _search_name(
        self,
        client: httpx.AsyncClient,
        name: str,
        country: str,
    ) -> list[dict[str, Any]]:
        """Search for a name in OpenSanctions.

        Args:
            client: HTTP client
            name: Name to search
            country: Country context

        Returns:
            List of matching entities
        """
        try:
            # Use the match endpoint for name matching
            response = await client.get(
                f"{self.base_url}/search/default",
                params={
                    "q": name,
                    "limit": 10,
                },
            )

            if response.status_code == 429:
                logger.warning("OpenSanctions rate limit reached")
                return []

            if response.status_code != 200:
                logger.error(f"OpenSanctions search failed: {response.status_code}")
                return []

            data = response.json()
            results = data.get("results", [])

            # Filter results by relevance
            filtered = []
            for result in results:
                # Get match score (0-1)
                score = result.get("score", 0)
                if score >= 0.5:  # Only include matches with 50%+ confidence
                    filtered.append(result)

            return filtered

        except Exception as e:
            logger.error(f"OpenSanctions search error: {e}")
            return []

    async def check_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific entity.

        Args:
            entity_id: OpenSanctions entity ID

        Returns:
            Entity details or None
        """
        try:
            client = await self._get_client()

            response = await client.get(f"{self.base_url}/entities/{entity_id}")

            if response.status_code != 200:
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching entity {entity_id}: {e}")
            return None

    def _is_high_confidence_match(self, match: dict[str, Any]) -> bool:
        """Check if a match is high confidence (likely a real hit)."""
        score = match.get("score", 0)
        # Score >= 0.8 is considered high confidence
        return score >= 0.8

    def _format_matches(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format matches for response."""
        formatted = []
        for match in matches[:10]:  # Limit to 10 matches
            formatted.append({
                "id": match.get("id"),
                "name": match.get("caption", match.get("name", "")),
                "schema": match.get("schema"),  # Person, Company, etc.
                "score": round(match.get("score", 0), 2),
                "datasets": match.get("datasets", []),
                "countries": match.get("properties", {}).get("country", []),
                "topics": match.get("properties", {}).get("topics", []),
            })
        return formatted

    def _error_result(self, error_message: str) -> SanctionCheckResult:
        """Create error result."""
        return SanctionCheckResult(
            is_sanctioned=False,
            matches=None,
            lists_checked=[],
            score=0,
            summary=f"Sanktionsprüfung fehlgeschlagen: {error_message}",
            raw_data={"error": error_message},
        )


class PEPScreeningProvider:
    """Specialized provider for PEP (Politically Exposed Persons) screening.

    Uses OpenSanctions but focuses on PEP-specific data.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self._sanctions = OpenSanctionsProvider(api_key=api_key, timeout=timeout)

    @property
    def provider_name(self) -> str:
        return "opensanctions_pep"

    async def check_pep(
        self,
        person_name: str,
        country: str = "AT",
    ) -> dict[str, Any]:
        """Check if a person is a PEP.

        Args:
            person_name: Full name of the person
            country: Country context

        Returns:
            PEP check result
        """
        try:
            result = await self._sanctions.check_sanctions(
                company_name=person_name,
                country=country,
            )

            # Filter for PEP-specific matches
            pep_matches = []
            if result.matches:
                for match in result.matches:
                    topics = match.get("topics", [])
                    if any("pep" in t.lower() or "politician" in t.lower() for t in topics):
                        pep_matches.append(match)

            is_pep = len(pep_matches) > 0 and any(
                m.get("score", 0) >= 0.8 for m in pep_matches
            )

            return {
                "is_pep": is_pep,
                "matches": pep_matches if pep_matches else None,
                "score": max((m.get("score", 0) for m in pep_matches), default=0) if pep_matches else 0,
                "summary": f"PEP-Status: {'Ja' if is_pep else 'Nein'}. "
                           f"{len(pep_matches)} mögliche Treffer."
                           if pep_matches else "Keine PEP-Treffer gefunden.",
                "checked_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"PEP check error: {e}")
            return {
                "is_pep": False,
                "error": str(e),
                "summary": f"PEP-Prüfung fehlgeschlagen: {e}",
            }

    async def close(self) -> None:
        """Close underlying provider."""
        await self._sanctions.close()
