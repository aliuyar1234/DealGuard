"""RIS (Rechtsinformationssystem) tools for Claude.

These tools provide access to Austrian federal and state laws,
court decisions, and legal indices.
"""

import logging
from typing import Literal

from dealguard.mcp.ris_client import RISClient, RISRestClient

logger = logging.getLogger(__name__)

# Global client instance (reused across calls)
_ris_client: RISClient | None = None
_ris_rest_client: RISRestClient | None = None


async def get_ris_client() -> RISClient:
    """Get or create the RIS client."""
    global _ris_client
    if _ris_client is None:
        _ris_client = RISClient()
    return _ris_client


async def get_ris_rest_client() -> RISRestClient:
    """Get or create the RIS REST client."""
    global _ris_rest_client
    if _ris_rest_client is None:
        _ris_rest_client = RISRestClient()
    return _ris_rest_client


async def search_ris(
    query: str,
    law_type: Literal["Bundesrecht", "Landesrecht", "Justiz", "Vfgh", "Vwgh"] = "Bundesrecht",
    limit: int = 5,
) -> str:
    """Search Austrian legal database (RIS) for laws and court decisions.

    Args:
        query: Search terms (e.g., "Kündigungsfrist Mietvertrag")
        law_type: Type of legal source to search:
            - "Bundesrecht": Federal laws (ABGB, UGB, KSchG, etc.)
            - "Landesrecht": State laws
            - "Justiz": Supreme Court (OGH) decisions
            - "Vfgh": Constitutional Court decisions
            - "Vwgh": Administrative Court decisions
        limit: Maximum number of results

    Returns:
        Formatted string with search results
    """
    try:
        # Try REST API first (more reliable)
        rest_client = await get_ris_rest_client()

        if law_type == "Bundesrecht":
            results = await rest_client.search_bundesrecht(query, limit)
        else:
            # Fall back to SOAP for non-Bundesrecht
            client = await get_ris_client()
            soap_results = await client.search(query, law_type, limit)
            results = [
                {
                    "Dokumentnummer": r.document_number,
                    "Kurztitel": r.title,
                    "Abkuerzung": r.abbreviation,
                    "ArtikelParagraphAnlage": r.paragraph,
                    "Index": r.index,
                }
                for r in soap_results
            ]

        if not results:
            return f"Keine Ergebnisse gefunden für: {query}\n\nTipps:\n- Verwende allgemeinere Suchbegriffe\n- Prüfe die Schreibweise\n- Versuche Synonyme"

        # Format results
        output = [f"# RIS Suchergebnisse für: {query}\n"]
        output.append(f"Gefunden: {len(results)} Ergebnisse in {law_type}\n")

        for i, item in enumerate(results[:limit], 1):
            doc_nr = item.get("Dokumentnummer", "")
            title = item.get("Kurztitel", "Unbekannt")
            abbrev = item.get("Abkuerzung", "")
            para = item.get("ArtikelParagraphAnlage", "")
            index = item.get("Index", "")

            output.append(f"\n## {i}. {title}")
            if abbrev and para:
                output.append(f"**{abbrev} {para}**")
            elif abbrev:
                output.append(f"**{abbrev}**")

            output.append(f"- Dokumentnummer: `{doc_nr}`")
            if index:
                output.append(f"- Index: {index}")
            output.append(f'- Verwende `get_law_text("{doc_nr}")` für den Volltext')

        return "\n".join(output)

    except Exception as e:
        logger.exception("Error searching RIS")
        return f"Fehler bei der RIS-Suche: {str(e)}"


async def get_law_text(document_number: str) -> str:
    """Get the full text of a specific law paragraph from RIS.

    Args:
        document_number: RIS document number (e.g., "NOR40000001")

    Returns:
        Full text of the law paragraph
    """
    try:
        client = await get_ris_client()
        doc = await client.get_document(document_number)

        if doc is None:
            return f"Dokument nicht gefunden: {document_number}"

        # Format output
        output = [f"# {doc.title}"]

        if doc.abbreviation and doc.paragraph:
            output.append(f"**{doc.abbreviation} {doc.paragraph}**")
        elif doc.abbreviation:
            output.append(f"**{doc.abbreviation}**")

        output.append(f"\n*Dokumentnummer: {doc.document_number}*")

        if doc.changed_date:
            output.append(f"*Letzte Änderung: {doc.changed_date}*")

        if doc.full_text:
            output.append("\n---\n")
            output.append(doc.full_text)
        else:
            output.append("\n---\n")
            output.append("*Volltext nicht direkt verfügbar.*")

            if doc.content_urls:
                output.append("\nVerfügbare Dokumente:")
                for url in doc.content_urls:
                    output.append(f"- {url}")

        return "\n".join(output)

    except Exception as e:
        logger.exception("Error getting law text")
        return f"Fehler beim Abrufen des Gesetzestexts: {str(e)}"


# Convenience functions for common use cases


async def search_abgb(query: str, limit: int = 5) -> str:
    """Search specifically in ABGB (Civil Code)."""
    return await search_ris(f"ABGB {query}", "Bundesrecht", limit)


async def search_ugb(query: str, limit: int = 5) -> str:
    """Search specifically in UGB (Commercial Code)."""
    return await search_ris(f"UGB {query}", "Bundesrecht", limit)


async def search_ogh(query: str, limit: int = 5) -> str:
    """Search OGH (Supreme Court) decisions."""
    return await search_ris(query, "Justiz", limit)
