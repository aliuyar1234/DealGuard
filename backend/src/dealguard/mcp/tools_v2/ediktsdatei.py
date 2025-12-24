"""Ediktsdatei tools for MCP v2."""

from __future__ import annotations

import json

from dealguard.mcp.models import ResponseFormat, SearchEdiktsdateiInput
from dealguard.mcp.tools_v2.common import (
    format_pagination_info,
    handle_error,
    truncate_response,
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
