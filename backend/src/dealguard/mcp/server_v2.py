"""DealGuard MCP Server v2 - Built with FastMCP best practices.

This server provides Claude with tools to access Austrian legal and business data:
- RIS (Rechtsinformationssystem): Austrian laws and court decisions
- Ediktsdatei: Insolvency and auction data
- Firmenbuch: Austrian company registry (via OpenFirmenbuch)
- OpenSanctions: International sanctions and PEP screening
- DealGuard DB: User's contracts, partners, and deadlines

Key improvements over v1:
- FastMCP framework with proper tool registration
- Pydantic v2 models for input validation
- Tool annotations (readOnlyHint, destructiveHint, etc.)
- Response format options (markdown/json)
- Proper pagination with has_more, next_offset
- Character limits and truncation
- Actionable error messages for LLMs

Usage with Claude Code:
    Add to your .claude/settings.json:
    {
        "mcpServers": {
            "dealguard": {
                "command": "python",
                "args": ["-m", "dealguard.mcp.server_v2"],
                "env": {"DATABASE_URL": "postgresql://..."}
            }
        }
    }
"""

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from dealguard.mcp.models import (
    ResponseFormat,
    SearchRISInput,
    GetLawTextInput,
    SearchEdiktsdateiInput,
    SearchFirmenbuchInput,
    GetFirmenbuchAuszugInput,
    CheckCompanyAustriaInput,
    CheckSanctionsInput,
    CheckPEPInput,
    ComprehensiveComplianceInput,
    SearchContractsInput,
    GetContractInput,
    GetPartnersInput,
    GetDeadlinesInput,
)

# Configure logging - use stderr for MCP servers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("dealguard_mcp")

# Constants
CHARACTER_LIMIT = 25000  # Maximum response size in characters


# ============================================================================
# Shared Utilities
# ============================================================================

def truncate_response(result: str, item_count: int = 0) -> str:
    """Truncate response if it exceeds CHARACTER_LIMIT."""
    if len(result) <= CHARACTER_LIMIT:
        return result

    # Truncate and add message
    truncated = result[:CHARACTER_LIMIT - 500]
    truncation_msg = (
        f"\n\n---\n**Hinweis:** Antwort gekürzt (von {len(result)} auf {CHARACTER_LIMIT} Zeichen). "
    )
    if item_count > 0:
        truncation_msg += f"Verwende 'offset' Parameter oder Filter für weitere Ergebnisse."
    return truncated + truncation_msg


def format_pagination_info(total: int, count: int, offset: int, limit: int) -> dict[str, Any]:
    """Generate standard pagination metadata."""
    return {
        "total": total,
        "count": count,
        "offset": offset,
        "has_more": total > offset + count,
        "next_offset": offset + count if total > offset + count else None,
    }


def handle_error(e: Exception, context: str) -> str:
    """Generate actionable error messages for LLMs."""
    error_type = type(e).__name__

    if "timeout" in str(e).lower():
        return (
            f"Fehler bei {context}: Zeitüberschreitung. "
            "Versuche es erneut oder verwende spezifischere Suchbegriffe."
        )
    elif "connection" in str(e).lower():
        return (
            f"Fehler bei {context}: Verbindung fehlgeschlagen. "
            "Der externe Dienst ist möglicherweise nicht erreichbar."
        )
    elif "not found" in str(e).lower() or "404" in str(e):
        return f"Fehler bei {context}: Ressource nicht gefunden. Prüfe die ID/Nummer."
    else:
        logger.exception(f"Error in {context}")
        return f"Fehler bei {context}: {error_type} - {str(e)}"


# ============================================================================
# RIS Tools (Austrian Legal Database)
# ============================================================================

@mcp.tool(
    name="dealguard_search_ris",
    annotations={
        "title": "RIS Gesetzessuche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
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
        results = await client.search_bundesrecht(params.query, params.limit)

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

        # Markdown format
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
            lines.append(f"- → `dealguard_get_law_text(document_number=\"{doc_nr}\")` für Volltext")
            lines.append("")

        return truncate_response("\n".join(lines), len(results))

    except Exception as e:
        return handle_error(e, "RIS-Suche")


@mcp.tool(
    name="dealguard_get_law_text",
    annotations={
        "title": "RIS Gesetzestext abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
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
        doc = await client.get_document(params.document_number)

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

        # Markdown format
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


# ============================================================================
# Ediktsdatei Tools (Insolvency Database)
# ============================================================================

@mcp.tool(
    name="dealguard_search_insolvency",
    annotations={
        "title": "Insolvenz-Suche (Ediktsdatei)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_search_insolvency(params: SearchEdiktsdateiInput) -> str:
    """Durchsucht die österreichische Ediktsdatei nach Insolvenzen.

    KRITISCH für Partner-Prüfung! Prüfe IMMER die Ediktsdatei bevor du
    Aussagen über die Bonität eines Unternehmens machst!

    Was gefunden werden kann:
    - Konkurse (Bankruptcy)
    - Sanierungsverfahren (Restructuring)
    - Zwangsversteigerungen (Forced auctions)
    - Pfändungen (Seizures)

    Args:
        params: Validierte Eingabeparameter mit:
            - name (str): Firmenname oder Personenname
            - bundesland (Bundesland): Optional, Filter nach Bundesland
            - limit (int): Maximale Ergebnisse
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Gefundene Insolvenzverfahren oder "Keine Treffer"

    Beispiel:
        dealguard_search_insolvency(name="ABC GmbH") → Insolvenzstatus
    """
    try:
        from dealguard.mcp.ediktsdatei_client import EdiktsdateiClient

        client = EdiktsdateiClient()
        bundesland = params.bundesland.value if params.bundesland else None
        results = await client.search(params.name, bundesland)

        if not results:
            return (
                f"✅ Keine Insolvenzverfahren gefunden für: '{params.name}'\n\n"
                "*Hinweis: Dies bedeutet nur, dass aktuell keine Einträge existieren. "
                "Für vollständige Due Diligence prüfe auch dealguard_check_company_austria().*"
            )

        if params.response_format == ResponseFormat.JSON:
            response = {
                **format_pagination_info(len(results), min(len(results), params.limit), 0, params.limit),
                "search_name": params.name,
                "results": results[:params.limit],
            }
            return json.dumps(response, indent=2, ensure_ascii=False)

        # Markdown format
        lines = [
            f"# ⚠️ Ediktsdatei Ergebnisse: '{params.name}'",
            f"**ACHTUNG:** {len(results)} Einträge gefunden!",
            "",
        ]

        for i, item in enumerate(results[:params.limit], 1):
            lines.append(f"## {i}. {item.get('name', 'Unbekannt')}")
            lines.append(f"- Aktenzeichen: {item.get('aktenzeichen', '-')}")
            lines.append(f"- Verfahrensart: {item.get('verfahrensart', '-')}")
            lines.append(f"- Gericht: {item.get('gericht', '-')}")
            lines.append(f"- Datum: {item.get('datum', '-')}")
            lines.append("")

        lines.append("---")
        lines.append("**⚠️ Bei Treffern: Vor Vertragsabschluss rechtliche Beratung einholen!**")

        return truncate_response("\n".join(lines), len(results))

    except Exception as e:
        return handle_error(e, "Ediktsdatei-Suche")


# ============================================================================
# Firmenbuch Tools (Company Registry)
# ============================================================================

@mcp.tool(
    name="dealguard_search_companies",
    annotations={
        "title": "Firmenbuch Suche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_search_companies(params: SearchFirmenbuchInput) -> str:
    """Durchsucht das österreichische Firmenbuch nach Unternehmen.

    Liefert offizielle Firmendaten: Name, FN-Nummer, Rechtsform, Sitz.
    Ideal für Partner-Recherche und Due Diligence in Österreich.

    Args:
        params: Validierte Eingabeparameter mit:
            - query (str): Firmenname oder Teil davon
            - limit (int): Maximale Ergebnisse (1-20)
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Liste gefundener Unternehmen mit FN-Nummern

    Beispiele:
        - "Red Bull" → Red Bull GmbH, FN 123456a
        - "OMV" → OMV AG und Tochtergesellschaften
    """
    try:
        from dealguard.infrastructure.external.openfirmenbuch import OpenFirmenbuchClient

        client = OpenFirmenbuchClient()
        results = await client.search(params.query, params.limit)

        if not results:
            return (
                f"Keine Unternehmen gefunden für: '{params.query}'\n\n"
                "**Tipps:**\n"
                "- Prüfe die Schreibweise\n"
                "- Verwende den offiziellen Firmennamen\n"
                "- Versuche Teile des Namens (z.B. 'Erste' statt 'Erste Bank')"
            )

        if params.response_format == ResponseFormat.JSON:
            response = {
                **format_pagination_info(len(results), len(results), 0, params.limit),
                "query": params.query,
                "companies": results,
            }
            return json.dumps(response, indent=2, ensure_ascii=False)

        # Markdown format
        lines = [
            f"# Firmenbuch Ergebnisse: '{params.query}'",
            f"Gefunden: {len(results)} Unternehmen",
            "",
        ]

        for i, company in enumerate(results, 1):
            fn = company.get("firmenbuchnummer", "-")
            name = company.get("name", "Unbekannt")
            rechtsform = company.get("rechtsform", "")
            sitz = company.get("sitz", "")

            lines.append(f"## {i}. {name}")
            lines.append(f"- FN: `{fn}`")
            if rechtsform:
                lines.append(f"- Rechtsform: {rechtsform}")
            if sitz:
                lines.append(f"- Sitz: {sitz}")
            lines.append(f"- → `dealguard_get_company_details(firmenbuchnummer=\"{fn}\")` für Details")
            lines.append("")

        return truncate_response("\n".join(lines), len(results))

    except Exception as e:
        return handle_error(e, "Firmenbuch-Suche")


@mcp.tool(
    name="dealguard_get_company_details",
    annotations={
        "title": "Firmenbuch Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_get_company_details(params: GetFirmenbuchAuszugInput) -> str:
    """Holt detaillierte Firmendaten aus dem Firmenbuch.

    Liefert: Geschäftsführer, Stammkapital, Unternehmensgegenstand, etc.
    Wichtig für Due Diligence und Partner-Verifizierung.

    Args:
        params: Validierte Eingabeparameter mit:
            - firmenbuchnummer (str): FN-Nummer (z.B. "123456a")
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Detaillierte Firmendaten

    Beispiel:
        dealguard_get_company_details(firmenbuchnummer="123456a")
    """
    try:
        from dealguard.infrastructure.external.openfirmenbuch import OpenFirmenbuchClient

        client = OpenFirmenbuchClient()
        company = await client.get_details(params.firmenbuchnummer)

        if not company:
            return (
                f"Firma nicht gefunden: FN {params.firmenbuchnummer}\n\n"
                "**Mögliche Gründe:**\n"
                "- FN-Nummer falsch geschrieben\n"
                "- Firma gelöscht/aufgelöst\n"
                "→ Verwende dealguard_search_companies() um aktuelle FN zu finden"
            )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(company, indent=2, ensure_ascii=False)

        # Markdown format
        lines = [
            f"# {company.get('name', 'Unbekannt')}",
            f"**FN: {params.firmenbuchnummer}**",
            "",
            "## Basisdaten",
            f"- Rechtsform: {company.get('rechtsform', '-')}",
            f"- Sitz: {company.get('sitz', '-')}",
            f"- Geschäftsanschrift: {company.get('adresse', '-')}",
        ]

        if company.get('stammkapital'):
            lines.append(f"- Stammkapital: {company['stammkapital']}")

        if company.get('gruendungsdatum'):
            lines.append(f"- Gegründet: {company['gruendungsdatum']}")

        gf = company.get('geschaeftsfuehrer', [])
        if gf:
            lines.extend(["", "## Geschäftsführer"])
            for person in gf:
                lines.append(f"- {person}")

        gegenstand = company.get('unternehmensgegenstand')
        if gegenstand:
            lines.extend([
                "",
                "## Unternehmensgegenstand",
                gegenstand,
            ])

        return truncate_response("\n".join(lines))

    except Exception as e:
        return handle_error(e, "Firmenbuch-Abruf")


@mcp.tool(
    name="dealguard_check_company_austria",
    annotations={
        "title": "Schnelle Firmenprüfung AT",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_check_company_austria(params: CheckCompanyAustriaInput) -> str:
    """Schnelle Prüfung eines österreichischen Unternehmens.

    Kombiniert Firmenbuch-Suche mit Basis-Check. Ideal für schnelle
    Partner-Verifizierung und erste Due Diligence.

    Args:
        params: Validierte Eingabeparameter mit:
            - company_name (str): Name des Unternehmens
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Zusammenfassung der Firmendaten oder Fehlermeldung
    """
    try:
        from dealguard.infrastructure.external.openfirmenbuch import OpenFirmenbuchClient

        client = OpenFirmenbuchClient()

        # Search first
        results = await client.search(params.company_name, 1)

        if not results:
            return (
                f"❌ Keine österreichische Firma gefunden: '{params.company_name}'\n\n"
                "**Mögliche Gründe:**\n"
                "- Firma nicht in Österreich registriert\n"
                "- Anderer offizieller Name\n"
                "- Prüfe Schreibweise\n\n"
                "→ Für deutsche Firmen: Handelsregister.de"
            )

        company = results[0]
        fn = company.get("firmenbuchnummer", "")

        # Get details
        details = await client.get_details(fn) if fn else {}

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "found": True,
                "company": {**company, **details},
            }, indent=2, ensure_ascii=False)

        # Markdown format
        lines = [
            f"# ✅ Firma gefunden: {company.get('name', params.company_name)}",
            "",
            f"- **FN:** {fn}",
            f"- **Rechtsform:** {company.get('rechtsform', '-')}",
            f"- **Sitz:** {company.get('sitz', '-')}",
        ]

        if details.get('geschaeftsfuehrer'):
            lines.append(f"- **Geschäftsführer:** {', '.join(details['geschaeftsfuehrer'])}")

        if details.get('stammkapital'):
            lines.append(f"- **Stammkapital:** {details['stammkapital']}")

        lines.extend([
            "",
            "---",
            "**Empfohlene weitere Prüfungen:**",
            f"- `dealguard_search_insolvency(name=\"{params.company_name}\")` → Insolvenzstatus",
            f"- `dealguard_check_sanctions(name=\"{params.company_name}\")` → Sanktionslisten",
        ])

        return "\n".join(lines)

    except Exception as e:
        return handle_error(e, "Firmenprüfung AT")


# ============================================================================
# Sanctions Tools
# ============================================================================

@mcp.tool(
    name="dealguard_check_sanctions",
    annotations={
        "title": "Sanktionslisten-Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_check_sanctions(params: CheckSanctionsInput) -> str:
    """Prüft ob ein Unternehmen/Person auf internationalen Sanktionslisten steht.

    Durchsucht:
    - EU Sanktionslisten (CFSP)
    - UN Consolidated Sanctions
    - US OFAC SDN List
    - UK HMT Sanctions
    - Schweizer SECO Liste

    ⚠️ WICHTIG: Bei Treffern KEINE Geschäftsbeziehung ohne rechtliche Klärung!

    Args:
        params: Validierte Eingabeparameter mit:
            - name (str): Name des Unternehmens oder der Person
            - country (str): ISO-2 Ländercode (default: AT)
            - aliases (list[str]): Alternative Namen (optional)
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Sanktionsstatus mit Details bei Treffern
    """
    try:
        from dealguard.infrastructure.external.opensanctions import OpenSanctionsClient

        client = OpenSanctionsClient()
        result = await client.check_sanctions(
            name=params.name,
            country=params.country,
            aliases=params.aliases,
        )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, ensure_ascii=False)

        if result.get("is_sanctioned"):
            matches = result.get("matches", [])
            lines = [
                f"# ⚠️ SANKTIONSTREFFER: {params.name}",
                "",
                f"**{len(matches)} Treffer auf Sanktionslisten!**",
                "",
            ]

            for match in matches:
                lines.append(f"## {match.get('name', 'Unbekannt')}")
                lines.append(f"- Liste: {match.get('dataset', '-')}")
                lines.append(f"- Grund: {match.get('reason', '-')}")
                lines.append(f"- Match-Score: {match.get('score', 0):.0%}")
                lines.append("")

            lines.extend([
                "---",
                "**⛔ HANDLUNGSEMPFEHLUNG:**",
                "- Keine Geschäftsbeziehung eingehen/fortführen",
                "- Rechtliche Beratung einholen",
                "- Ggf. Meldepflichten prüfen (GwG)",
            ])

            return "\n".join(lines)
        else:
            return (
                f"# ✅ Keine Sanktionstreffer: {params.name}\n\n"
                f"Geprüfte Listen: EU, UN, US OFAC, UK HMT, CH SECO\n\n"
                "*Hinweis: Dies ist ein Screening-Tool. Für rechtlich verbindliche "
                "Prüfungen professionelle Compliance-Dienste nutzen.*"
            )

    except Exception as e:
        return handle_error(e, "Sanktionsprüfung")


@mcp.tool(
    name="dealguard_check_pep",
    annotations={
        "title": "PEP-Prüfung",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_check_pep(params: CheckPEPInput) -> str:
    """Prüft ob eine Person ein PEP (Politically Exposed Person) ist.

    Wichtig für KYC/AML Compliance und Geldwäsche-Prävention.
    Bei PEPs gelten erhöhte Sorgfaltspflichten (Enhanced Due Diligence).

    PEP-Kategorien:
    - Staatsoberhäupter, Regierungsmitglieder
    - Parlamentarier
    - Mitglieder oberster Gerichte
    - Botschafter, hohe Militärs
    - Führungskräfte staatlicher Unternehmen
    - Familienmitglieder und enge Vertraute der o.g.

    Args:
        params: Validierte Eingabeparameter mit:
            - person_name (str): Vollständiger Name der Person
            - country (str): ISO-2 Ländercode (default: AT)
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: PEP-Status mit Details
    """
    try:
        from dealguard.infrastructure.external.opensanctions import OpenSanctionsClient

        client = OpenSanctionsClient()
        result = await client.check_pep(
            name=params.person_name,
            country=params.country,
        )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, ensure_ascii=False)

        if result.get("is_pep"):
            lines = [
                f"# ⚠️ PEP IDENTIFIZIERT: {params.person_name}",
                "",
            ]

            for match in result.get("matches", []):
                lines.append(f"## {match.get('name', 'Unbekannt')}")
                lines.append(f"- Position: {match.get('position', '-')}")
                lines.append(f"- Land: {match.get('country', '-')}")
                lines.append(f"- Match-Score: {match.get('score', 0):.0%}")
                lines.append("")

            lines.extend([
                "---",
                "**📋 HANDLUNGSEMPFEHLUNG (Enhanced Due Diligence):**",
                "- Erweiterte Identitätsprüfung durchführen",
                "- Herkunft der Mittel klären",
                "- Geschäftsbeziehung dokumentieren",
                "- Regelmäßige Überprüfung einrichten",
                "- Ggf. Genehmigung der Geschäftsleitung einholen",
            ])

            return "\n".join(lines)
        else:
            return (
                f"# ✅ Kein PEP: {params.person_name}\n\n"
                "Keine Treffer in PEP-Datenbanken gefunden.\n\n"
                "*Hinweis: Standard-Sorgfaltspflichten anwenden.*"
            )

    except Exception as e:
        return handle_error(e, "PEP-Prüfung")


@mcp.tool(
    name="dealguard_comprehensive_compliance",
    annotations={
        "title": "Compliance-Vollprüfung",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def dealguard_comprehensive_compliance(params: ComprehensiveComplianceInput) -> str:
    """Umfassende Compliance-Prüfung: Sanktionen + PEP in einem Aufruf.

    Ideal für Onboarding neuer Geschäftspartner und Due Diligence.
    Kombiniert Sanktionslisten-Prüfung und PEP-Screening.

    Args:
        params: Validierte Eingabeparameter mit:
            - name (str): Name des Unternehmens oder der Person
            - entity_type (EntityType): "company" oder "person"
            - country (str): ISO-2 Ländercode (default: AT)
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Umfassender Compliance-Report
    """
    try:
        from dealguard.infrastructure.external.opensanctions import OpenSanctionsClient

        client = OpenSanctionsClient()
        result = await client.comprehensive_check(
            name=params.name,
            entity_type=params.entity_type.value,
            country=params.country,
        )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, ensure_ascii=False)

        # Determine overall status
        is_clean = not result.get("is_sanctioned") and not result.get("is_pep")
        status_emoji = "✅" if is_clean else "⚠️"
        status_text = "CLEAR" if is_clean else "PRÜFUNG ERFORDERLICH"

        lines = [
            f"# {status_emoji} Compliance-Report: {params.name}",
            f"**Status: {status_text}**",
            f"- Typ: {params.entity_type.value}",
            f"- Land: {params.country}",
            "",
            "## Prüfergebnisse",
            "",
            f"### Sanktionslisten: {'⚠️ TREFFER' if result.get('is_sanctioned') else '✅ Keine Treffer'}",
        ]

        if result.get("sanction_matches"):
            for match in result["sanction_matches"]:
                lines.append(f"- {match.get('name')}: {match.get('dataset')}")

        lines.append(f"\n### PEP-Status: {'⚠️ PEP' if result.get('is_pep') else '✅ Kein PEP'}")

        if result.get("pep_matches"):
            for match in result["pep_matches"]:
                lines.append(f"- {match.get('name')}: {match.get('position')}")

        if not is_clean:
            lines.extend([
                "",
                "---",
                "**📋 Empfohlene Maßnahmen:**",
                "- Detailprüfung der Treffer durchführen",
                "- Rechtliche Beratung einholen",
                "- Dokumentation erstellen",
            ])

        return "\n".join(lines)

    except Exception as e:
        return handle_error(e, "Compliance-Prüfung")


# ============================================================================
# DealGuard DB Tools
# ============================================================================

@mcp.tool(
    name="dealguard_search_contracts",
    annotations={
        "title": "Verträge durchsuchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,  # Internal database
    }
)
async def dealguard_search_contracts(params: SearchContractsInput, organization_id: str | None = None) -> str:
    """Durchsucht die Verträge des Benutzers nach Stichwörtern.

    Findet relevante Vertragsklauseln die mit einer Rechtsfrage zusammenhängen.
    Nützlich um Vertragstexte mit Gesetzestexten zu vergleichen.

    Args:
        params: Validierte Eingabeparameter mit:
            - query (str): Suchbegriffe (z.B. "Kündigungsfrist", "Haftung")
            - contract_type (str): Optional, Vertragstyp filtern
            - limit (int): Maximale Ergebnisse (1-50)
            - offset (int): Für Pagination
            - response_format (ResponseFormat): markdown oder json
        organization_id: Internal - wird automatisch gesetzt

    Returns:
        str: Gefundene Verträge mit relevanten Textausschnitten
    """
    try:
        # Import here to avoid circular imports
        from dealguard.mcp.tools.db_tools import search_contracts as db_search

        result = await db_search(
            query=params.query,
            contract_type=params.contract_type,
            limit=params.limit,
            organization_id=organization_id,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Vertragssuche")


@mcp.tool(
    name="dealguard_get_contract",
    annotations={
        "title": "Vertrag abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def dealguard_get_contract(params: GetContractInput, organization_id: str | None = None) -> str:
    """Holt die Details eines spezifischen Vertrags inkl. AI-Analyse.

    Liefert den vollständigen Text und die bereits durchgeführte Risikoanalyse.

    Args:
        params: Validierte Eingabeparameter mit:
            - contract_id (str): UUID des Vertrags
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Vertragsdetails mit Text und Analyse
    """
    try:
        from dealguard.mcp.tools.db_tools import get_contract as db_get

        result = await db_get(
            contract_id=params.contract_id,
            organization_id=organization_id,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Vertragsabruf")


@mcp.tool(
    name="dealguard_get_partners",
    annotations={
        "title": "Partner auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def dealguard_get_partners(params: GetPartnersInput, organization_id: str | None = None) -> str:
    """Listet alle Geschäftspartner des Benutzers mit Risiko-Scores.

    Nützlich für Überblick und um Partner für weitere Prüfungen zu identifizieren.

    Args:
        params: Validierte Eingabeparameter mit:
            - risk_level (RiskLevel): Optional, nach Risikostufe filtern
            - limit (int): Maximale Ergebnisse (1-100)
            - offset (int): Für Pagination
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Liste der Partner mit Risiko-Scores
    """
    try:
        from dealguard.mcp.tools.db_tools import get_partners as db_get

        risk_level = params.risk_level.value if params.risk_level else None
        result = await db_get(
            risk_level=risk_level,
            limit=params.limit,
            organization_id=organization_id,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Partner-Abruf")


@mcp.tool(
    name="dealguard_get_deadlines",
    annotations={
        "title": "Fristen abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def dealguard_get_deadlines(params: GetDeadlinesInput, organization_id: str | None = None) -> str:
    """Holt anstehende Fristen aus den Verträgen des Benutzers.

    WICHTIG: Verwende dies proaktiv wenn der Benutzer nach Fristen fragt
    oder wenn du eine Übersicht geben sollst.

    Arten von Fristen:
    - Kündigungsfristen
    - Zahlungsfristen
    - Vertragsverlängerungen
    - Review-Termine

    Args:
        params: Validierte Eingabeparameter mit:
            - days_ahead (int): Wie viele Tage vorausschauen (1-365)
            - include_overdue (bool): Überfällige Fristen einschließen
            - limit (int): Maximale Ergebnisse (1-100)
            - response_format (ResponseFormat): markdown oder json

    Returns:
        str: Liste der anstehenden Fristen nach Dringlichkeit sortiert
    """
    try:
        from dealguard.mcp.tools.db_tools import get_deadlines as db_get

        result = await db_get(
            days_ahead=params.days_ahead,
            include_overdue=params.include_overdue,
            organization_id=organization_id,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Fristenabruf")


# ============================================================================
# Tool Definitions Export (for Claude API integration)
# ============================================================================

def _resolve_refs(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve $ref references in a JSON schema."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            # Extract ref name (e.g., "#/$defs/LawType" -> "LawType")
            ref_path = schema["$ref"]
            ref_name = ref_path.split("/")[-1]
            if ref_name in defs:
                # Merge the referenced definition with any additional properties
                resolved = defs[ref_name].copy()
                # Keep any additional properties from the original (like default, description)
                for key, value in schema.items():
                    if key != "$ref":
                        resolved[key] = value
                return resolved
            return schema
        else:
            return {k: _resolve_refs(v, defs) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [_resolve_refs(item, defs) for item in schema]
    else:
        return schema


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get tool definitions in Claude API format.

    This converts FastMCP tool definitions to the format expected by
    the Anthropic Claude API for tool_use.

    FastMCP wraps parameters in a 'params' object and uses $refs for
    enums. We need to:
    1. Extract the actual input model from $defs
    2. Resolve all $ref references inline
    """
    tools = []

    for tool in mcp._tool_manager._tools.values():
        parameters = tool.parameters
        defs = parameters.get("$defs", {})

        # Find the main input model (the one ending with "Input")
        input_model_name = None
        input_model = None
        for name, definition in defs.items():
            if name.endswith("Input"):
                input_model_name = name
                input_model = definition.copy()
                break

        if input_model is None:
            # Fallback: use the full parameters schema
            input_schema = parameters
        else:
            # Resolve all $ref references in the input model
            input_schema = _resolve_refs(input_model, defs)
            # Remove $defs from the resolved schema if it exists
            input_schema.pop("$defs", None)

        tool_def = {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": input_schema,
        }
        tools.append(tool_def)

    return tools


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
