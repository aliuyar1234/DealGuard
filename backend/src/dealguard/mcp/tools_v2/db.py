"""DealGuard DB tools for MCP v2."""

from __future__ import annotations

from uuid import UUID

from dealguard.config import get_settings
from dealguard.mcp.models import (
    GetContractInput,
    GetDeadlinesInput,
    GetPartnersInput,
    SearchContractsInput,
)
from dealguard.mcp.tools.db_tools import DbToolContext, build_db_tool_context
from dealguard.mcp.tools_v2.common import handle_error, truncate_response


async def dealguard_search_contracts(
    params: SearchContractsInput,
    organization_id: str | None = None,
) -> str:
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
        if not organization_id:
            return "Fehler: Keine Organisation im Kontext. Bitte einloggen."

        ctx = _build_context(organization_id)
        from dealguard.mcp.tools.db_tools import search_contracts as db_search

        result = await db_search(
            ctx,
            query=params.query,
            contract_type=params.contract_type,
            limit=params.limit,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Vertragssuche")


async def dealguard_get_contract(
    params: GetContractInput,
    organization_id: str | None = None,
) -> str:
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
        if not organization_id:
            return "Fehler: Keine Organisation im Kontext."

        ctx = _build_context(organization_id)
        from dealguard.mcp.tools.db_tools import get_contract as db_get

        result = await db_get(
            ctx,
            contract_id=params.contract_id,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Vertragsabruf")


async def dealguard_get_partners(
    params: GetPartnersInput,
    organization_id: str | None = None,
) -> str:
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
        if not organization_id:
            return "Fehler: Keine Organisation im Kontext."

        ctx = _build_context(organization_id)
        from dealguard.mcp.tools.db_tools import get_partners as db_get

        risk_level = params.risk_level.value if params.risk_level else None
        result = await db_get(
            ctx,
            risk_level=risk_level,
            limit=params.limit,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Partner-Abruf")


async def dealguard_get_deadlines(
    params: GetDeadlinesInput,
    organization_id: str | None = None,
) -> str:
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
        if not organization_id:
            return "Fehler: Keine Organisation im Kontext."

        ctx = _build_context(organization_id)
        from dealguard.mcp.tools.db_tools import get_deadlines as db_get

        result = await db_get(
            ctx,
            days_ahead=params.days_ahead,
            include_overdue=params.include_overdue,
        )

        return truncate_response(result)

    except Exception as e:
        return handle_error(e, "Fristenabruf")


def _build_context(organization_id: str) -> DbToolContext:
    settings = get_settings()
    try:
        org_uuid = UUID(organization_id)
    except ValueError as exc:
        raise ValueError("Ungültige organization_id") from exc
    return build_db_tool_context(str(settings.database_url), org_uuid)
