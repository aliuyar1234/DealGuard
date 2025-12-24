"""RIS tools for MCP v2."""

from __future__ import annotations

import json

from dealguard.mcp.models import GetLawTextInput, ResponseFormat, SearchRISInput
from dealguard.mcp.tools_v2.common import (
    format_pagination_info,
    handle_error,
    truncate_response,
)


async def dealguard_search_ris(params: SearchRISInput) -> str:
    """Durchsucht das österreichische Rechtsinformationssystem (RIS) nach Gesetzen.

    WICHTIG: Nutze dieses Tool IMMER wenn du Gesetzestexte zitieren sollst!
    Halluziniere niemals Paragraphen - hole sie aus dem RIS!

    Verfügbare Rechtsquellen:
    - Bundesrecht: ABGB, UGB, KSchG, GmbHG, AktG, MRG, etc.
    - Landesrecht: Landesgesetze der 9 Bundesländer
    - Justiz: OGH (Oberster Gerichtshof) Entscheidungen
    - Vfgh: Verfassungsgerichtshof Entscheidungen
    - Vwgh: Verwaltungsgerichtshof Entscheidungen

    Args:
        params: Validierte Eingabeparameter mit:
            - query (str): Suchbegriffe (z.B. "Kündigungsfrist ABGB", "Gewährleistung")
            - law_type (LawType): Art der Rechtsquelle (default: Bundesrecht)
            - limit (int): Maximale Ergebnisse (1-20, default: 5)
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Suchergebnisse mit Dokumentnummern für get_law_text()

    Beispiele:
        - "Kündigungsfrist Mietvertrag" → Findet §1116 ABGB
        - "Gewährleistung Kauf" → Findet §§922-933 ABGB
        - "GmbH Geschäftsführer Haftung" → Findet §25 GmbHG
    """
    try:
        from dealguard.mcp.ris_client import RISRestClient

        client = RISRestClient()
        try:
            results = await client.search_bundesrecht(params.query, params.limit)
        finally:
            await client.close()

        if not results:
            return (
                f"Keine Ergebnisse für: '{params.query}'\n\n"
                "**Tipps:**\n"
                "- Verwende allgemeinere Suchbegriffe\n"
                "- Prüfe die Schreibweise\n"
                "- Versuche Synonyme (z.B. 'Miete' statt 'Bestandvertrag')"
            )

        if params.response_format == ResponseFormat.JSON:
            response = {
                **format_pagination_info(len(results), len(results), 0, params.limit),
                "query": params.query,
                "law_type": params.law_type.value,
                "results": results,
            }
            return json.dumps(response, indent=2, ensure_ascii=False)

        lines = [
            f"# RIS Suchergebnisse: '{params.query}'",
            f"Gefunden: {len(results)} Ergebnisse in {params.law_type.value}",
            "",
        ]

        for i, item in enumerate(results, 1):
            doc_nr = item.get("Dokumentnummer", "")
            title = item.get("Kurztitel", "Unbekannt")
            abbrev = item.get("Abkuerzung", "")
            para = item.get("ArtikelParagraphAnlage", "")

            lines.append(f"## {i}. {title}")
            if abbrev and para:
                lines.append(f"**{abbrev} {para}**")
            lines.append(f"- Dokumentnummer: `{doc_nr}`")
            lines.append(f'- → `dealguard_get_law_text(document_number="{doc_nr}")` für Volltext')
            lines.append("")

        return truncate_response("\n".join(lines), len(results))

    except Exception as e:
        return handle_error(e, "RIS-Suche")


async def dealguard_get_law_text(params: GetLawTextInput) -> str:
    """Holt den vollständigen Text eines Paragraphen aus dem RIS.

    Verwende dies nach dealguard_search_ris(), um den exakten Gesetzestext zu erhalten.
    Die Dokumentnummer erhältst du aus den Suchergebnissen.

    Args:
        params: Validierte Eingabeparameter mit:
            - document_number (str): RIS Dokumentnummer (z.B. "NOR40000001")
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Vollständiger Gesetzestext mit Metadaten

    Beispiel:
        dealguard_get_law_text(document_number="NOR40000001") → Volltext §1116 ABGB
    """
    try:
        from dealguard.mcp.ris_client import RISClient

        client = RISClient()
        try:
            doc = await client.get_document(params.document_number)
        finally:
            await client.close()

        if doc is None:
            return (
                f"Dokument nicht gefunden: {params.document_number}\n\n"
                "**Mögliche Gründe:**\n"
                "- Dokumentnummer falsch geschrieben\n"
                "- Dokument nicht mehr aktuell\n"
                "→ Verwende dealguard_search_ris() um aktuelle Dokumentnummern zu finden"
            )

        if params.response_format == ResponseFormat.JSON:
            response = {
                "document_number": doc.document_number,
                "title": doc.title,
                "abbreviation": doc.abbreviation,
                "paragraph": doc.paragraph,
                "changed_date": doc.changed_date,
                "full_text": doc.full_text,
                "content_urls": doc.content_urls,
            }
            return json.dumps(response, indent=2, ensure_ascii=False)

        lines = [f"# {doc.title}"]

        if doc.abbreviation and doc.paragraph:
            lines.append(f"**{doc.abbreviation} {doc.paragraph}**")

        lines.append(f"\n*Dokumentnummer: {doc.document_number}*")

        if doc.changed_date:
            lines.append(f"*Letzte Änderung: {doc.changed_date}*")

        if doc.full_text:
            lines.extend(["\n---\n", doc.full_text])
        else:
            lines.append("\n*Volltext nicht direkt verfügbar.*")

        return truncate_response("\n".join(lines))

    except Exception as e:
        return handle_error(e, "RIS Dokumentabruf")
