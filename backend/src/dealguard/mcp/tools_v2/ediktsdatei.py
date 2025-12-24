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
        from dealguard.mcp.ediktsdatei_client import (
            Bundesland as ClientBundesland,
        )
        from dealguard.mcp.ediktsdatei_client import (
            EdiktsdateiClient,
            InsolvenzEdikt,
        )

        client = EdiktsdateiClient()
        try:
            client_bundesland = (
                ClientBundesland(params.bundesland.value) if params.bundesland else None
            )
            search_result = await client.search_insolvenzen(
                name=params.name,
                bundesland=client_bundesland,
                limit=params.limit,
                page=1,
            )
        finally:
            await client.close()

        if not search_result.items:
            return (
                f"✅ Keine Insolvenzverfahren gefunden für: '{params.name}'\n\n"
                "*Hinweis: Dies bedeutet nur, dass aktuell keine Einträge existieren. "
                "Für vollständige Due Diligence prüfe auch dealguard_check_company_austria().*"
            )

        if params.response_format == ResponseFormat.JSON:
            results = []
            for item in search_result.items[: params.limit]:
                if isinstance(item, InsolvenzEdikt):
                    results.append(
                        {
                            "name": item.schuldner_name,
                            "aktenzeichen": item.aktenzeichen,
                            "verfahrensart": item.verfahrensart,
                            "status": item.status,
                            "gericht": item.gericht,
                            "kundmachungsdatum": item.kundmachungsdatum.isoformat(),
                            "eroeffnungsdatum": item.eroeffnungsdatum.isoformat()
                            if item.eroeffnungsdatum
                            else None,
                            "frist_forderungsanmeldung": item.frist_forderungsanmeldung.isoformat()
                            if item.frist_forderungsanmeldung
                            else None,
                            "details_url": item.details_url,
                        }
                    )

            response = {
                **format_pagination_info(
                    search_result.total,
                    min(len(search_result.items), params.limit),
                    0,
                    params.limit,
                ),
                "search_name": params.name,
                "results": results,
            }
            return json.dumps(response, indent=2, ensure_ascii=False)

        lines = [
            f"# ⚠️ Ediktsdatei Ergebnisse: '{params.name}'",
            f"**ACHTUNG:** {len(search_result.items)} Einträge gefunden!",
            "",
        ]

        for i, item in enumerate(search_result.items[: params.limit], 1):
            if not isinstance(item, InsolvenzEdikt):
                continue

            lines.append(f"## {i}. {item.schuldner_name}")
            lines.append(f"- Aktenzeichen: {item.aktenzeichen}")
            lines.append(f"- Verfahrensart: {item.verfahrensart}")
            lines.append(f"- Gericht: {item.gericht}")
            lines.append(f"- Datum: {item.kundmachungsdatum.isoformat()}")
            lines.append("")

        lines.append("---")
        lines.append("**⚠️ Bei Treffern: Vor Vertragsabschluss rechtliche Beratung einholen!**")

        return truncate_response("\n".join(lines), len(search_result.items))

    except Exception as e:
        return handle_error(e, "Ediktsdatei-Suche")
