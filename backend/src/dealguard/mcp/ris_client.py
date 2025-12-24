"""Client for Austrian RIS (Rechtsinformationssystem) OGD API.

The RIS OGD API provides free access to Austrian federal and state laws,
court decisions (OGH, VwGH, VfGH), and EU law references.

API Documentation: https://github.com/ximex/ris-bka/blob/master/RIS_OGD_Dokumentation.md
Endpoint: http://data.bka.gv.at/ris/OGDService.asmx
"""

import logging
from dataclasses import dataclass
from typing import Any, Literal, cast
from xml.etree import ElementTree
from xml.sax.saxutils import escape as _xml_escape

import httpx
from defusedxml import ElementTree as DefusedElementTree

logger = logging.getLogger(__name__)

RIS_URL = "http://data.bka.gv.at/ris/OGDService.asmx"

# RIS Application types
RISApplikation = Literal[
    "Bundesrecht",
    "BgblAuth",
    "Landesrecht",
    "Gemeinderecht",
    "Justiz",
    "Vfgh",
    "Vwgh",
    "Normenliste",
    "Erlaesse",
    "PrBE",
]

# SOAP namespaces
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
RIS_NS = "http://ris.bka.gv.at/"


def _escape_xml_text(value: str) -> str:
    return _xml_escape(value, {'"': "&quot;", "'": "&apos;"})


@dataclass
class RISSearchResult:
    """A single search result from RIS."""

    document_number: str  # e.g., "NOR40000001"
    title: str  # Title of the law/paragraph
    abbreviation: str | None  # e.g., "ABGB"
    paragraph: str | None  # e.g., "§ 1116"
    article_type: str | None  # Type of article
    index: str | None  # RIS index
    changed_date: str | None  # Last change date
    application: str  # Which RIS application this is from


@dataclass
class RISDocument:
    """A full document from RIS."""

    document_number: str
    title: str
    abbreviation: str | None
    paragraph: str | None
    full_text: str  # The actual law text (HTML or plain)
    content_urls: list[str]  # URLs to content (PDF, HTML, etc.)
    index: str | None
    changed_date: str | None
    application: str


class RISClient:
    """Client for the Austrian RIS (Rechtsinformationssystem) OGD API.

    This client provides access to:
    - Bundesrecht (Federal laws: ABGB, UGB, KSchG, etc.)
    - Landesrecht (State laws for all 9 Austrian states)
    - Justiz (Court decisions: OGH)
    - Vfgh (Constitutional Court decisions)
    - Vwgh (Administrative Court decisions)

    Example usage:
        client = RISClient()

        # Search for laws about contract termination
        results = await client.search("Kündigungsfrist Mietvertrag")

        # Get full text of a specific paragraph
        doc = await client.get_document("NOR40000001")
    """

    def __init__(self, timeout: float = 30.0):
        """Initialize the RIS client.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_search_request(
        self,
        query: str,
        application: RISApplikation = "Bundesrecht",
        limit: int = 10,
        page: int = 1,
    ) -> str:
        """Build SOAP request for RIS search.

        The RIS API uses a specific XML format for search requests.
        See: https://data.bka.gv.at/ris/OGDService.asmx?op=request
        """
        application_xml = _escape_xml_text(application)
        query_xml = _escape_xml_text(query)

        # RIS expects specific XML structure
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ris="http://ris.bka.gv.at/">
  <soap:Body>
    <ris:request>
      <ris:application>{application_xml}</ris:application>
      <ris:query>
        <ris:searchTerms>{query_xml}</ris:searchTerms>
        <ris:pageNumber>{page}</ris:pageNumber>
        <ris:pageSize>{limit}</ris:pageSize>
      </ris:query>
    </ris:request>
  </soap:Body>
</soap:Envelope>"""
        return soap_request

    def _build_document_request(
        self,
        document_number: str,
        application: RISApplikation = "Bundesrecht",
    ) -> str:
        """Build SOAP request for fetching a specific document."""
        application_xml = _escape_xml_text(application)
        document_number_xml = _escape_xml_text(document_number)

        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ris="http://ris.bka.gv.at/">
  <soap:Body>
    <ris:getDocument>
      <ris:application>{application_xml}</ris:application>
      <ris:documentNumber>{document_number_xml}</ris:documentNumber>
    </ris:getDocument>
  </soap:Body>
</soap:Envelope>"""
        return soap_request

    def _parse_search_response(
        self,
        xml_response: str,
        application: str,
    ) -> list[RISSearchResult]:
        """Parse the XML response from a search request."""
        results: list[RISSearchResult] = []

        try:
            root = cast(ElementTree.Element, DefusedElementTree.fromstring(xml_response))

            # Find all document elements in the response
            # The exact structure depends on the RIS response format
            for doc in root.iter():
                if doc.tag.endswith("OgdDocumentReference") or doc.tag.endswith("Document"):
                    result = self._parse_document_reference(doc, application)
                    if result:
                        results.append(result)

        except Exception as e:
            logger.error(f"Failed to parse RIS search response: {e}")

        return results

    def _parse_document_reference(
        self,
        element: ElementTree.Element,
        application: str,
    ) -> RISSearchResult | None:
        """Parse a single document reference from search results."""
        try:
            # Helper to get text from child element
            def get_text(tag_suffix: str) -> str | None:
                for child in element.iter():
                    if child.tag.endswith(tag_suffix) and child.text:
                        return child.text.strip()
                return None

            document_number = get_text("Dokumentnummer") or get_text("DocumentNumber")
            if not document_number:
                return None

            return RISSearchResult(
                document_number=document_number,
                title=get_text("Kurztitel") or get_text("Title") or "Unbekannt",
                abbreviation=get_text("Abkuerzung") or get_text("Abbreviation"),
                paragraph=get_text("Paragraph") or get_text("ArtikelParagraphAnlage"),
                article_type=get_text("Typ") or get_text("ArticleType"),
                index=get_text("Index"),
                changed_date=get_text("Aenderungsdatum") or get_text("ChangedDate"),
                application=application,
            )
        except Exception as e:
            logger.warning(f"Failed to parse document reference: {e}")
            return None

    def _parse_document_response(
        self,
        xml_response: str,
        application: str,
        ) -> RISDocument | None:
        """Parse the XML response from a document request."""
        try:
            root = cast(ElementTree.Element, DefusedElementTree.fromstring(xml_response))

            # Helper to get text from element
            def get_text(tag_suffix: str) -> str | None:
                for elem in root.iter():
                    if elem.tag.endswith(tag_suffix) and elem.text:
                        return elem.text.strip()
                return None

            # Get all content URLs
            content_urls: list[str] = []
            for elem in root.iter():
                if elem.tag.endswith("ContentUrl") or elem.tag.endswith("DokumentUrl"):
                    url = elem.text
                    if url:
                        content_urls.append(url.strip())

            document_number = get_text("Dokumentnummer") or get_text("DocumentNumber")
            if not document_number:
                return None

            # Try to get the full text content
            full_text = ""
            for elem in root.iter():
                if (elem.tag.endswith("Inhalt") or elem.tag.endswith("Content")) and elem.text:
                    full_text = elem.text.strip()
                    break

            return RISDocument(
                document_number=document_number,
                title=get_text("Kurztitel") or get_text("Title") or "Unbekannt",
                abbreviation=get_text("Abkuerzung") or get_text("Abbreviation"),
                paragraph=get_text("Paragraph") or get_text("ArtikelParagraphAnlage"),
                full_text=full_text,
                content_urls=content_urls,
                index=get_text("Index"),
                changed_date=get_text("Aenderungsdatum") or get_text("ChangedDate"),
                application=application,
            )

        except Exception as e:
            logger.error(f"Failed to parse RIS document response: {e}")
            return None

    async def search(
        self,
        query: str,
        application: RISApplikation = "Bundesrecht",
        limit: int = 10,
        page: int = 1,
    ) -> list[RISSearchResult]:
        """Search for laws and legal documents in RIS.

        Args:
            query: Search terms (e.g., "Kündigungsfrist Mietvertrag")
            application: Which RIS database to search:
                - "Bundesrecht": Federal laws (ABGB, UGB, KSchG, etc.)
                - "Landesrecht": State laws
                - "Justiz": OGH court decisions
                - "Vfgh": Constitutional Court
                - "Vwgh": Administrative Court
            limit: Maximum number of results (default: 10)
            page: Page number for pagination (default: 1)

        Returns:
            List of matching documents with metadata
        """
        client = await self._get_client()

        soap_body = self._build_search_request(query, application, limit, page)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://ris.bka.gv.at/request",
        }

        try:
            response = await client.post(
                RIS_URL,
                content=soap_body.encode("utf-8"),
                headers=headers,
            )
            response.raise_for_status()

            return self._parse_search_response(response.text, application)

        except httpx.HTTPError as e:
            logger.error(f"RIS API request failed: {e}")
            return []

    async def get_document(
        self,
        document_number: str,
        application: RISApplikation = "Bundesrecht",
    ) -> RISDocument | None:
        """Get the full text of a specific legal document.

        Args:
            document_number: The RIS document number (e.g., "NOR40000001")
            application: Which RIS database the document is from

        Returns:
            Full document with text content, or None if not found
        """
        client = await self._get_client()

        soap_body = self._build_document_request(document_number, application)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://ris.bka.gv.at/getDocument",
        }

        try:
            response = await client.post(
                RIS_URL,
                content=soap_body.encode("utf-8"),
                headers=headers,
            )
            response.raise_for_status()

            return self._parse_document_response(response.text, application)

        except httpx.HTTPError as e:
            logger.error(f"RIS API document request failed: {e}")
            return None

    async def search_bundesrecht(
        self,
        query: str,
        limit: int = 10,
    ) -> list[RISSearchResult]:
        """Convenience method to search federal laws (ABGB, UGB, etc.)."""
        return await self.search(query, "Bundesrecht", limit)

    async def search_ogh(
        self,
        query: str,
        limit: int = 10,
    ) -> list[RISSearchResult]:
        """Convenience method to search OGH (Supreme Court) decisions."""
        return await self.search(query, "Justiz", limit)

    async def search_vfgh(
        self,
        query: str,
        limit: int = 10,
    ) -> list[RISSearchResult]:
        """Convenience method to search VfGH (Constitutional Court) decisions."""
        return await self.search(query, "Vfgh", limit)


# Alternative REST-based approach using the newer OGD JSON API
# This is a fallback if SOAP doesn't work well

RIS_JSON_URL = "https://data.bka.gv.at/ris/api/v2.6"


class RISRestClient:
    """Alternative REST client for RIS using the newer JSON API.

    The JSON API may be more reliable than SOAP for some use cases.
    Base URL: https://data.bka.gv.at/ris/api/v2.6
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search_bundesrecht(
        self,
        search_text: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Austrian federal laws using REST API.

        Args:
            search_text: Search terms
            limit: Max results

        Returns:
            List of result dictionaries
        """
        client = await self._get_client()

        # RIS API requires 'Titel' parameter for text search
        params = {
            "Titel": search_text,
            "PageNumber": "1",
            "PageSize": str(limit),
        }

        try:
            response = await client.get(
                f"{RIS_JSON_URL}/Bundesrecht",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            results = (
                data.get("OgdSearchResult", {})
                .get("OgdDocumentResults", {})
                .get("OgdDocumentReference", [])
            )

            # Handle single result (API returns dict instead of list)
            if isinstance(results, dict):
                results = [results]

            # Transform nested structure to flat dict
            flat_results = []
            for item in results:
                data_section = item.get("Data", {}).get("Metadaten", {})
                bundesrecht = data_section.get("Bundesrecht", {})
                technisch = data_section.get("Technisch", {})

                flat_results.append(
                    {
                        "Dokumentnummer": technisch.get("ID", ""),
                        "Kurztitel": bundesrecht.get("Kurztitel", ""),
                        "Titel": bundesrecht.get("Titel", ""),
                        "Index": data_section.get("Allgemein", {}).get("DokumentUrl", ""),
                    }
                )

            return flat_results

        except httpx.HTTPError as e:
            logger.error(f"RIS REST API request failed: {e}")
            return []
