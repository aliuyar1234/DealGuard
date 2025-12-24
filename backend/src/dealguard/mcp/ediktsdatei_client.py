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
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx

from dealguard.shared.exceptions import ExternalServiceError

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


_AKTENZEICHEN_RE = re.compile(r"\b\d+\s*[A-Z]?\s*\d+/\d+\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b|\b\d{4}-\d{2}-\d{2}\b")


class _EdikteHTMLParser(HTMLParser):
    """Collect rows and links from HTML tables for best-effort scraping."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, list[str]]] = []
        self._in_row = False
        self._in_cell = False
        self._cell_chunks: list[str] = []
        self._row_cells: list[str] = []
        self._row_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._in_row = True
            self._row_cells = []
            self._row_links = []
        elif self._in_row and tag in ("td", "th"):
            self._in_cell = True
            self._cell_chunks = []
        elif self._in_cell and tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._row_links.append(href)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._in_cell:
            text = " ".join("".join(self._cell_chunks).split())
            self._row_cells.append(text)
            self._cell_chunks = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if any(cell for cell in self._row_cells):
                self.rows.append(
                    {"cells": self._row_cells, "links": self._row_links}
                )
            self._in_row = False


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

            try:
                data = response.json()
            except ValueError:
                logger.warning(
                    "ediktsdatei_invalid_json",
                    status=response.status_code,
                )
                return await self._scrape_insolvenz_search(name, bundesland, limit)

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

        except ExternalServiceError:
            raise

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
                raise ExternalServiceError(
                    f"Ediktsdatei HTML-Suche fehlgeschlagen (Status {response.status_code})"
                )

            html = response.text
            html_lower = html.lower()
            if "keine" in html_lower and ("treffer" in html_lower or "ergebnisse" in html_lower):
                return EdikteSearchResult(total=0, page=1, page_size=limit, items=[])

            parser = _EdikteHTMLParser()
            parser.feed(html)
            rows = parser.rows
            if not rows:
                raise ExternalServiceError(
                    "Ediktsdatei HTML konnte nicht geparst werden (keine Tabellenzeilen)."
                )

            header_idx = None
            header_cells: list[str] = []
            for idx, row in enumerate(rows):
                cells = [cell.lower() for cell in row["cells"]]
                if any("aktenzeichen" in cell or cell == "az" for cell in cells) and any(
                    "schuldner" in cell or "name" in cell for cell in cells
                ):
                    header_idx = idx
                    header_cells = cells
                    break

            items: list[InsolvenzEdikt] = []

            if header_idx is not None:
                def find_col(keys: tuple[str, ...]) -> int | None:
                    for i, cell in enumerate(header_cells):
                        if any(key in cell for key in keys):
                            return i
                    return None

                idx_az = find_col(("aktenzeichen", "az"))
                idx_name = find_col(("schuldner", "name"))
                idx_gericht = find_col(("gericht",))
                idx_art = find_col(("verfahrensart", "art"))
                idx_status = find_col(("status",))
                idx_datum = find_col(("kundmach", "datum"))
                idx_frist = find_col(("frist",))
                idx_verwalter = find_col(("verwalter",))

                for row in rows[header_idx + 1 :]:
                    cells = row["cells"]
                    if not any(cells):
                        continue

                    def cell_at(col_idx: int | None) -> str:
                        if col_idx is None or col_idx >= len(cells):
                            return ""
                        return cells[col_idx].strip()

                    aktenzeichen = cell_at(idx_az)
                    schuldner = cell_at(idx_name)
                    gericht = cell_at(idx_gericht)
                    verfahrensart = cell_at(idx_art)
                    status = cell_at(idx_status)
                    kundmachung = self._parse_date(cell_at(idx_datum)) or date.today()
                    frist = self._parse_date(cell_at(idx_frist))
                    verwalter = cell_at(idx_verwalter) or None

                    if not schuldner and not aktenzeichen and not gericht:
                        continue

                    details_url = (
                        urljoin(EDIKTE_BASE_URL, row["links"][0])
                        if row["links"]
                        else f"{EDIKTE_BASE_URL}/edikte/insolvenz"
                    )

                    items.append(
                        InsolvenzEdikt(
                            id=aktenzeichen or f"scraped-{len(items) + 1}",
                            aktenzeichen=aktenzeichen,
                            gericht=gericht,
                            gericht_code="",
                            schuldner_name=schuldner,
                            schuldner_adresse=None,
                            verfahrensart=verfahrensart,
                            status=status,
                            eroeffnungsdatum=None,
                            kundmachungsdatum=kundmachung,
                            frist_forderungsanmeldung=frist,
                            insolvenzverwalter=verwalter,
                            details_url=details_url,
                        )
                    )
                if not items:
                    return EdikteSearchResult(
                        total=0,
                        page=1,
                        page_size=limit,
                        items=[],
                    )
            else:
                for row in rows:
                    row_text = " ".join(row["cells"])
                    akten_match = _AKTENZEICHEN_RE.search(row_text)
                    date_match = _DATE_RE.search(row_text)

                    aktenzeichen = akten_match.group(0) if akten_match else ""
                    kundmachung = self._parse_date(date_match.group(0)) if date_match else None

                    gericht = ""
                    for cell in row["cells"]:
                        cell_lower = cell.lower()
                        if "gericht" in cell_lower or cell_lower.startswith(("lg", "bg", "hg")):
                            gericht = cell
                            break

                    schuldner = ""
                    for cell in row["cells"]:
                        cell_lower = cell.lower()
                        if (
                            cell
                            and cell != aktenzeichen
                            and not _DATE_RE.search(cell)
                            and "gericht" not in cell_lower
                        ):
                            schuldner = cell
                            break

                    if not schuldner and not aktenzeichen and not gericht:
                        continue

                    details_url = (
                        urljoin(EDIKTE_BASE_URL, row["links"][0])
                        if row["links"]
                        else f"{EDIKTE_BASE_URL}/edikte/insolvenz"
                    )

                    items.append(
                        InsolvenzEdikt(
                            id=aktenzeichen or f"scraped-{len(items) + 1}",
                            aktenzeichen=aktenzeichen,
                            gericht=gericht,
                            gericht_code="",
                            schuldner_name=schuldner,
                            schuldner_adresse=None,
                            verfahrensart="",
                            status="",
                            eroeffnungsdatum=None,
                            kundmachungsdatum=kundmachung or date.today(),
                            frist_forderungsanmeldung=None,
                            insolvenzverwalter=None,
                            details_url=details_url,
                        )
                    )

            if not items:
                raise ExternalServiceError(
                    "Ediktsdatei HTML konnte nicht ausgewertet werden (keine verwertbaren Ergebnisse)."
                )

            items = items[:limit]
            return EdikteSearchResult(
                total=len(items),
                page=1,
                page_size=limit,
                items=items,
            )

        except ExternalServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to scrape Ediktsdatei: {e}")
            raise ExternalServiceError(
                "Ediktsdatei HTML-Suche fehlgeschlagen (unerwarteter Fehler)."
            ) from e

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
