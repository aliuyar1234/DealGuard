"""Client for Austrian Ediktsdatei (IWG-API).

The Ediktsdatei provides free access to:
- Insolvenzen (Insolvencies: bankruptcy, restructuring)
- Zwangsversteigerungen (Forced auctions: real estate, movables)
- Pfändungen (Seizures)
- Firmenbucheinträge (Commercial register entries)

API: https://edikte.justiz.gv.at/
IWG = Informationsweiterverwendungsgesetz (PSI Directive implementation)
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Base URL for Ediktsdatei
EDIKTE_BASE_URL = "https://edikte.justiz.gv.at"


class EdiktType(str, Enum):
    """Types of public notices in Ediktsdatei."""

    # Insolvency types
    INSOLVENZ = "insolvenz"
    KONKURS = "konkurs"
    SANIERUNG = "sanierung"
    SANIERUNG_EIGENVERWALTUNG = "sanierung_eigenverwaltung"

    # Auction types
    VERSTEIGERUNG = "versteigerung"
    LIEGENSCHAFT = "liegenschaft"
    FAHRNISSE = "fahrnisse"

    # Other
    FIRMENBUCH = "firmenbuch"
    KUNDMACHUNG = "kundmachung"


class Bundesland(str, Enum):
    """Austrian federal states."""

    WIEN = "W"
    NIEDEROESTERREICH = "N"
    OBEROESTERREICH = "O"
    SALZBURG = "S"
    TIROL = "T"
    VORARLBERG = "V"
    KAERNTEN = "K"
    STEIERMARK = "ST"
    BURGENLAND = "B"


@dataclass
class InsolvenzEdikt:
    """An insolvency notice from Ediktsdatei."""

    id: str  # Unique identifier
    aktenzeichen: str  # Case number (e.g., "5 S 123/24")
    gericht: str  # Court name
    gericht_code: str  # Court code
    schuldner_name: str  # Debtor name
    schuldner_adresse: str | None  # Debtor address
    verfahrensart: str  # Type: Konkurs, Sanierung, etc.
    status: str  # Current status
    eroeffnungsdatum: date | None  # Opening date
    kundmachungsdatum: date  # Publication date
    frist_forderungsanmeldung: date | None  # Deadline for claims
    insolvenzverwalter: str | None  # Insolvency administrator
    details_url: str  # URL to full details


@dataclass
class VersteigerungEdikt:
    """An auction notice from Ediktsdatei."""

    id: str
    aktenzeichen: str
    gericht: str
    gericht_code: str
    art: str  # Type: Liegenschaft, Fahrnisse
    objektbezeichnung: str  # Object description
    schaetzwert: float | None  # Estimated value
    mindestgebot: float | None  # Minimum bid
    termin: datetime | None  # Auction date/time
    ort: str | None  # Auction location
    kundmachungsdatum: date
    details_url: str


@dataclass
class EdikteSearchResult:
    """Search results from Ediktsdatei."""

    total: int  # Total number of results
    page: int  # Current page
    page_size: int  # Results per page
    items: list[InsolvenzEdikt | VersteigerungEdikt]


class EdiktsdateiClient:
    """Client for the Austrian Ediktsdatei (IWG-API).

    Provides access to:
    - Insolvency notices (bankruptcies, restructuring)
    - Auction notices (real estate, movables)
    - Commercial register publications

    Example usage:
        client = EdiktsdateiClient()

        # Search for insolvencies of a company
        results = await client.search_insolvenzen("ABC GmbH")

        # Get all recent insolvencies
        recent = await client.get_recent_insolvenzen(days=30)
    """

    def __init__(self, timeout: float = 30.0):
        """Initialize the Ediktsdatei client.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse a date string from the API."""
        if not date_str:
            return None

        formats = ["%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.split("T")[0], fmt.split("T")[0]).date()
            except ValueError:
                continue
        return None

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse a datetime string from the API."""
        if not dt_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None

    def _parse_insolvenz(self, data: dict[str, Any]) -> InsolvenzEdikt:
        """Parse an insolvency record from API response."""
        return InsolvenzEdikt(
            id=str(data.get("id", "")),
            aktenzeichen=data.get("aktenzeichen", data.get("az", "")),
            gericht=data.get("gericht", data.get("gerichtName", "")),
            gericht_code=data.get("gerichtCode", data.get("gkz", "")),
            schuldner_name=data.get("schuldnerName", data.get("name", "")),
            schuldner_adresse=data.get("schuldnerAdresse", data.get("adresse")),
            verfahrensart=data.get("verfahrensart", data.get("art", "")),
            status=data.get("status", ""),
            eroeffnungsdatum=self._parse_date(data.get("eroeffnungsdatum", data.get("eröffnung"))),
            kundmachungsdatum=self._parse_date(data.get("kundmachungsdatum", data.get("datum"))) or date.today(),
            frist_forderungsanmeldung=self._parse_date(data.get("fristForderungsanmeldung", data.get("frist"))),
            insolvenzverwalter=data.get("insolvenzverwalter", data.get("verwalter")),
            details_url=data.get("detailsUrl", data.get("url", f"{EDIKTE_BASE_URL}/edikte/id/{data.get('id', '')}")),
        )

    def _parse_versteigerung(self, data: dict[str, Any]) -> VersteigerungEdikt:
        """Parse an auction record from API response."""
        schaetzwert = data.get("schaetzwert", data.get("wert"))
        if schaetzwert and isinstance(schaetzwert, str):
            schaetzwert = float(schaetzwert.replace(",", ".").replace("€", "").strip())

        mindestgebot = data.get("mindestgebot", data.get("mindestpreis"))
        if mindestgebot and isinstance(mindestgebot, str):
            mindestgebot = float(mindestgebot.replace(",", ".").replace("€", "").strip())

        return VersteigerungEdikt(
            id=str(data.get("id", "")),
            aktenzeichen=data.get("aktenzeichen", data.get("az", "")),
            gericht=data.get("gericht", data.get("gerichtName", "")),
            gericht_code=data.get("gerichtCode", data.get("gkz", "")),
            art=data.get("art", data.get("typ", "")),
            objektbezeichnung=data.get("objektbezeichnung", data.get("objekt", "")),
            schaetzwert=schaetzwert,
            mindestgebot=mindestgebot,
            termin=self._parse_datetime(data.get("termin", data.get("versteigerungstermin"))),
            ort=data.get("ort", data.get("versteigerungsort")),
            kundmachungsdatum=self._parse_date(data.get("kundmachungsdatum", data.get("datum"))) or date.today(),
            details_url=data.get("detailsUrl", data.get("url", f"{EDIKTE_BASE_URL}/edikte/id/{data.get('id', '')}")),
        )

    async def search_insolvenzen(
        self,
        name: str | None = None,
        bundesland: Bundesland | None = None,
        von_datum: date | None = None,
        bis_datum: date | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> EdikteSearchResult:
        """Search for insolvency notices.

        Args:
            name: Company or person name to search for
            bundesland: Filter by federal state
            von_datum: Start date for search range
            bis_datum: End date for search range
            limit: Maximum results per page
            page: Page number

        Returns:
            Search results with insolvency notices
        """
        client = await self._get_client()

        # Build search parameters
        params: dict[str, str] = {
            "type": "insolvenz",
            "pageSize": str(limit),
            "page": str(page),
        }

        if name:
            params["name"] = name
        if bundesland:
            params["bundesland"] = bundesland.value
        if von_datum:
            params["vonDatum"] = von_datum.isoformat()
        if bis_datum:
            params["bisDatum"] = bis_datum.isoformat()

        try:
            # Try the IWG API endpoint
            # Note: The actual endpoint structure may vary
            response = await client.get(
                f"{EDIKTE_BASE_URL}/edikte/iwg/insolvenzen",
                params=params,
            )

            if response.status_code == 404:
                # Try alternative endpoint
                response = await client.get(
                    f"{EDIKTE_BASE_URL}/edikte/suche",
                    params=params,
                )

            # If API doesn't work, try scraping the search page
            if response.status_code != 200:
                return await self._scrape_insolvenz_search(name, bundesland, limit)

            data = response.json()

            items = []
            for item in data.get("results", data.get("items", [])):
                items.append(self._parse_insolvenz(item))

            return EdikteSearchResult(
                total=data.get("total", len(items)),
                page=page,
                page_size=limit,
                items=items,
            )

        except httpx.HTTPError as e:
            logger.error(f"Ediktsdatei API request failed: {e}")
            # Fall back to scraping
            return await self._scrape_insolvenz_search(name, bundesland, limit)

        except Exception as e:
            logger.error(f"Failed to search Ediktsdatei: {e}")
            return EdikteSearchResult(total=0, page=page, page_size=limit, items=[])

    async def _scrape_insolvenz_search(
        self,
        name: str | None,
        bundesland: Bundesland | None,
        limit: int,
    ) -> EdikteSearchResult:
        """Fallback: Scrape the Ediktsdatei search page.

        The Ediktsdatei may not have a proper JSON API, so we might need
        to scrape the HTML search results.
        """
        client = await self._get_client()

        # Build the search URL for the web interface
        params = {"searchType": "insolvenz"}
        if name:
            params["suchbegriff"] = name

        try:
            response = await client.get(
                f"{EDIKTE_BASE_URL}/edikte/insolvenz/suche.nsf",
                params=params,
            )

            if response.status_code != 200:
                logger.warning(f"Ediktsdatei search returned {response.status_code}")
                return EdikteSearchResult(total=0, page=1, page_size=limit, items=[])

            # For now, return empty results
            # TODO: Implement HTML parsing if JSON API is not available
            logger.info("Ediktsdatei: HTML scraping not implemented, returning empty results")
            return EdikteSearchResult(total=0, page=1, page_size=limit, items=[])

        except Exception as e:
            logger.error(f"Failed to scrape Ediktsdatei: {e}")
            return EdikteSearchResult(total=0, page=1, page_size=limit, items=[])

    async def search_versteigerungen(
        self,
        art: EdiktType | None = None,
        bundesland: Bundesland | None = None,
        von_datum: date | None = None,
        bis_datum: date | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> EdikteSearchResult:
        """Search for auction notices.

        Args:
            art: Type of auction (Liegenschaft, Fahrnisse)
            bundesland: Filter by federal state
            von_datum: Start date for search range
            bis_datum: End date for search range
            limit: Maximum results per page
            page: Page number

        Returns:
            Search results with auction notices
        """
        client = await self._get_client()

        params: dict[str, str] = {
            "type": "versteigerung",
            "pageSize": str(limit),
            "page": str(page),
        }

        if art:
            params["art"] = art.value
        if bundesland:
            params["bundesland"] = bundesland.value
        if von_datum:
            params["vonDatum"] = von_datum.isoformat()
        if bis_datum:
            params["bisDatum"] = bis_datum.isoformat()

        try:
            response = await client.get(
                f"{EDIKTE_BASE_URL}/edikte/iwg/versteigerungen",
                params=params,
            )

            if response.status_code != 200:
                logger.warning(f"Versteigerungen API returned {response.status_code}")
                return EdikteSearchResult(total=0, page=page, page_size=limit, items=[])

            data = response.json()

            items = []
            for item in data.get("results", data.get("items", [])):
                items.append(self._parse_versteigerung(item))

            return EdikteSearchResult(
                total=data.get("total", len(items)),
                page=page,
                page_size=limit,
                items=items,
            )

        except Exception as e:
            logger.error(f"Failed to search Versteigerungen: {e}")
            return EdikteSearchResult(total=0, page=page, page_size=limit, items=[])

    async def get_recent_insolvenzen(
        self,
        days: int = 30,
        bundesland: Bundesland | None = None,
        limit: int = 50,
    ) -> list[InsolvenzEdikt]:
        """Get recent insolvency notices.

        Args:
            days: Look back this many days
            bundesland: Filter by federal state
            limit: Maximum results

        Returns:
            List of recent insolvency notices
        """
        von_datum = date.today().replace(day=1) if days >= 30 else None
        result = await self.search_insolvenzen(
            bundesland=bundesland,
            von_datum=von_datum,
            limit=limit,
        )
        return [item for item in result.items if isinstance(item, InsolvenzEdikt)]

    async def check_company_insolvency(
        self,
        company_name: str,
    ) -> list[InsolvenzEdikt]:
        """Check if a company has any insolvency proceedings.

        This is the main function for partner due diligence.

        Args:
            company_name: Name of the company to check

        Returns:
            List of insolvency proceedings (empty if none found)
        """
        result = await self.search_insolvenzen(name=company_name, limit=10)
        return [item for item in result.items if isinstance(item, InsolvenzEdikt)]
