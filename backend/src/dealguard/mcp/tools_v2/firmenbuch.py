"""Firmenbuch tools for MCP v2."""

from __future__ import annotations

import json

from dealguard.mcp.models import (
    CheckCompanyAustriaInput,
    GetFirmenbuchAuszugInput,
    ResponseFormat,
    SearchFirmenbuchInput,
)
from dealguard.mcp.tools_v2.common import (
    format_pagination_info,
    handle_error,
    truncate_response,
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
            lines.append(
                f"- → `dealguard_get_company_details(firmenbuchnummer=\"{fn}\")` für Details"
            )
            lines.append("")

        return truncate_response("\n".join(lines), len(results))

    except Exception as e:
        return handle_error(e, "Firmenbuch-Suche")


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

        lines = [
            f"# {company.get('name', 'Unbekannt')}",
            f"**FN: {params.firmenbuchnummer}**",
            "",
            "## Basisdaten",
            f"- Rechtsform: {company.get('rechtsform', '-')}",
            f"- Sitz: {company.get('sitz', '-')}",
            f"- Geschäftsanschrift: {company.get('adresse', '-')}",
        ]

        if company.get("stammkapital"):
            lines.append(f"- Stammkapital: {company['stammkapital']}")

        if company.get("gruendungsdatum"):
            lines.append(f"- Gegründet: {company['gruendungsdatum']}")

        gf = company.get("geschaeftsfuehrer", [])
        if gf:
            lines.extend(["", "## Geschäftsführer"])
            for person in gf:
                lines.append(f"- {person}")

        gegenstand = company.get("unternehmensgegenstand")
        if gegenstand:
            lines.extend(
                [
                    "",
                    "## Unternehmensgegenstand",
                    gegenstand,
                ]
            )

        return truncate_response("\n".join(lines))

    except Exception as e:
        return handle_error(e, "Firmenbuch-Abruf")


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

        results = await client.search(params.company_name, 1)

        if not results:
            return (
                f"⌛ Keine österreichische Firma gefunden: '{params.company_name}'\n\n"
                "**Mögliche Gründe:**\n"
                "- Firma nicht in Österreich registriert\n"
                "- Anderer offizieller Name\n"
                "- Prüfe Schreibweise\n\n"
                "→ Für deutsche Firmen: Handelsregister.de"
            )

        company = results[0]
        fn = company.get("firmenbuchnummer", "")

        details = await client.get_details(fn) if fn else {}

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(
                {"found": True, "company": {**company, **details}},
                indent=2,
                ensure_ascii=False,
            )

        lines = [
            f"# ✅ Firma gefunden: {company.get('name', params.company_name)}",
            "",
            f"- **FN:** {fn}",
            f"- **Rechtsform:** {company.get('rechtsform', '-')}",
            f"- **Sitz:** {company.get('sitz', '-')}",
        ]

        if details.get("geschaeftsfuehrer"):
            lines.append(
                f"- **Geschäftsführer:** {', '.join(details['geschaeftsfuehrer'])}"
            )

        if details.get("stammkapital"):
            lines.append(f"- **Stammkapital:** {details['stammkapital']}")

        lines.extend(
            [
                "",
                "---",
                "**Empfohlene weitere Prüfungen:**",
                f"- `dealguard_search_insolvency(name=\"{params.company_name}\")` → Insolvenzstatus",
                f"- `dealguard_check_sanctions(name=\"{params.company_name}\")` → Sanktionslisten",
            ]
        )

        return "\n".join(lines)

    except Exception as e:
        return handle_error(e, "Firmenprüfung AT")
