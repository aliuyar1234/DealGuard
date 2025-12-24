"""Ediktsdatei tools for Claude.

These tools provide access to Austrian insolvency and auction data
from the official Ediktsdatei.
"""

import logging
from typing import Literal

from dealguard.mcp.ediktsdatei_client import (
    Bundesland,
    EdiktsdateiClient,
    InsolvenzEdikt,
)

logger = logging.getLogger(__name__)

# Global client instance
_edikte_client: EdiktsdateiClient | None = None


async def get_edikte_client() -> EdiktsdateiClient:
    """Get or create the Ediktsdatei client."""
    global _edikte_client
    if _edikte_client is None:
        _edikte_client = EdiktsdateiClient()
    return _edikte_client


def _format_insolvenz(insolvenz: InsolvenzEdikt) -> str:
    """Format an insolvency record for display."""
    lines = [
        f"### {insolvenz.schuldner_name}",
        f"**{insolvenz.verfahrensart}** - {insolvenz.status}",
        f"- Aktenzeichen: {insolvenz.aktenzeichen}",
        f"- Gericht: {insolvenz.gericht}",
    ]

    if insolvenz.eroeffnungsdatum:
        lines.append(f"- Eröffnet: {insolvenz.eroeffnungsdatum}")

    if insolvenz.frist_forderungsanmeldung:
        lines.append(f"- Frist Forderungsanmeldung: {insolvenz.frist_forderungsanmeldung}")

    if insolvenz.insolvenzverwalter:
        lines.append(f"- Insolvenzverwalter: {insolvenz.insolvenzverwalter}")

    if insolvenz.schuldner_adresse:
        lines.append(f"- Adresse: {insolvenz.schuldner_adresse}")

    lines.append(f"- Details: {insolvenz.details_url}")

    return "\n".join(lines)


async def search_ediktsdatei(
    name: str,
    bundesland: Literal["W", "N", "O", "S", "T", "V", "K", "ST", "B"] | None = None,
) -> str:
    """Search the Austrian Ediktsdatei for insolvencies.

    This is CRITICAL for partner due diligence! Always check before
    making statements about a company's financial health.

    Args:
        name: Company or person name to search for
        bundesland: Optional state filter:
            - W: Wien
            - N: Niederösterreich
            - O: Oberösterreich
            - S: Salzburg
            - T: Tirol
            - V: Vorarlberg
            - K: Kärnten
            - ST: Steiermark
            - B: Burgenland

    Returns:
        Formatted string with insolvency results
    """
    try:
        client = await get_edikte_client()

        # Convert bundesland string to enum
        bl = Bundesland(bundesland) if bundesland else None

        result = await client.search_insolvenzen(name=name, bundesland=bl, limit=10)

        if result.total == 0 or not result.items:
            return f"""# Ediktsdatei Suche: {name}

**Keine Insolvenzen gefunden.**

Dies bedeutet, dass zum Zeitpunkt der Abfrage kein aktives Insolvenzverfahren
für "{name}" in der Ediktsdatei eingetragen ist.

⚠️ **Hinweis:** Dies garantiert NICHT die Zahlungsfähigkeit des Unternehmens.
- Die Ediktsdatei enthält nur gerichtliche Insolvenzverfahren
- Ein Verfahren könnte noch nicht veröffentlicht sein
- Zahlungsschwierigkeiten ohne Insolvenzantrag werden nicht erfasst

Empfehlung: Für eine vollständige Bonitätsprüfung zusätzliche Quellen nutzen."""

        # Format results
        output = [
            f"# Ediktsdatei Suche: {name}",
            "",
            f"**⚠️ WARNUNG: {result.total} Insolvenzverfahren gefunden!**",
            "",
        ]

        for item in result.items:
            if isinstance(item, InsolvenzEdikt):
                output.append(_format_insolvenz(item))
                output.append("")

        output.append("---")
        output.append("*Quelle: Österreichische Ediktsdatei (edikte.justiz.gv.at)*")

        return "\n".join(output)

    except Exception as e:
        logger.exception("Error searching Ediktsdatei")
        return f"Fehler bei der Ediktsdatei-Suche: {str(e)}"


async def check_insolvency(company_name: str) -> str:
    """Quick check if a company has any insolvency proceedings.

    This is a simplified version of search_ediktsdatei focused on
    answering the question: "Is this company insolvent?"

    Args:
        company_name: Name of the company to check

    Returns:
        Clear answer about insolvency status
    """
    try:
        client = await get_edikte_client()
        insolvencies = await client.check_company_insolvency(company_name)

        if not insolvencies:
            return f"""## Insolvenzprüfung: {company_name}

✅ **Kein aktives Insolvenzverfahren gefunden.**

Zum Zeitpunkt der Abfrage ist kein Insolvenzverfahren in der
österreichischen Ediktsdatei eingetragen.

*Hinweis: Dies ist keine Garantie für Zahlungsfähigkeit.*"""

        # Found insolvencies
        latest = insolvencies[0]
        return f"""## Insolvenzprüfung: {company_name}

🚨 **AKTIVES INSOLVENZVERFAHREN GEFUNDEN!**

**{latest.verfahrensart}**
- Aktenzeichen: {latest.aktenzeichen}
- Gericht: {latest.gericht}
- Eröffnet: {latest.eroeffnungsdatum or "Unbekannt"}
- Status: {latest.status}

**Empfohlene Maßnahmen:**
1. Keine neuen Aufträge ohne Vorauszahlung
2. Offene Forderungen beim Insolvenzgericht anmelden
3. Bestehende Verträge auf Kündigungsrechte prüfen
4. Rechtliche Beratung einholen

*Quelle: Österreichische Ediktsdatei*"""

    except Exception as e:
        logger.exception("Error checking insolvency")
        return f"Fehler bei der Insolvenzprüfung: {str(e)}"


async def get_recent_insolvencies(
    days: int = 30,
    bundesland: Literal["W", "N", "O", "S", "T", "V", "K", "ST", "B"] | None = None,
) -> str:
    """Get recent insolvency notices.

    Useful for proactive monitoring of the market.

    Args:
        days: Look back this many days
        bundesland: Optional state filter

    Returns:
        List of recent insolvencies
    """
    try:
        client = await get_edikte_client()
        bl = Bundesland(bundesland) if bundesland else None

        insolvencies = await client.get_recent_insolvenzen(
            days=days,
            bundesland=bl,
            limit=20,
        )

        if not insolvencies:
            bl_name = f" in {bundesland}" if bundesland else ""
            return f"Keine neuen Insolvenzen in den letzten {days} Tagen{bl_name} gefunden."

        output = [
            f"# Aktuelle Insolvenzen (letzte {days} Tage)",
            "",
            f"Gefunden: {len(insolvencies)} Verfahren",
            "",
        ]

        for ins in insolvencies:
            output.append(f"- **{ins.schuldner_name}** ({ins.verfahrensart})")
            output.append(f"  - {ins.gericht}, {ins.aktenzeichen}")
            if ins.eroeffnungsdatum:
                output.append(f"  - Eröffnet: {ins.eroeffnungsdatum}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        logger.exception("Error getting recent insolvencies")
        return f"Fehler: {str(e)}"
