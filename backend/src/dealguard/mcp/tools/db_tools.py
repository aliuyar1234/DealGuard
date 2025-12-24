"""Database tools for Claude.

These tools provide read-only access to DealGuard's database:
- Contracts and their analyses
- Partners and risk scores
- Deadlines and alerts

Note: These tools require a valid organization context to work.
For the Chat API, the organization_id is provided by the authenticated user.
For the MCP Server, it needs to be provided via environment or configuration.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class DbToolContext:
    """Explicit database context for MCP DB tools."""

    session_factory: sessionmaker
    organization_id: UUID


def build_db_tool_context(database_url: str, organization_id: UUID) -> DbToolContext:
    """Build a DbToolContext with its own engine/session factory."""
    engine = create_async_engine(database_url)
    session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return DbToolContext(session_factory=session_factory, organization_id=organization_id)


def _format_contract(contract: dict[str, Any]) -> str:
    """Format a contract record for display."""
    lines = [
        f"### {contract.get('filename', 'Unbekannt')}",
        f"**Typ:** {contract.get('contract_type', 'Unbekannt')}",
        f"**Status:** {contract.get('status', 'Unbekannt')}",
    ]

    if contract.get("risk_score") is not None:
        score = contract["risk_score"]
        emoji = "🟢" if score < 30 else "🟡" if score < 60 else "🟠" if score < 80 else "🔴"
        lines.append(f"**Risiko:** {emoji} {score}/100")

    if contract.get("summary"):
        lines.append(f"\n*{contract['summary'][:200]}...*")

    lines.append(f"\n- ID: `{contract.get('id', '')}`")
    lines.append(f"- Hochgeladen: {contract.get('created_at', '')}")

    return "\n".join(lines)


def _format_partner(partner: dict[str, Any]) -> str:
    """Format a partner record for display."""
    risk_level = partner.get("risk_level", "unknown")
    emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "critical": "🔴",
    }.get(risk_level, "⚪")

    lines = [
        f"### {partner.get('name', 'Unbekannt')}",
        f"**Risiko:** {emoji} {risk_level.upper()}",
        f"**Typ:** {partner.get('partner_type', 'Unbekannt')}",
    ]

    if partner.get("risk_score") is not None:
        lines.append(f"**Score:** {partner['risk_score']}/100")

    if partner.get("registration_number"):
        lines.append(f"- FN: {partner['registration_number']}")

    if partner.get("country"):
        lines.append(f"- Land: {partner['country']}")

    lines.append(f"- ID: `{partner.get('id', '')}`")

    return "\n".join(lines)


def _format_deadline(deadline: dict[str, Any]) -> str:
    """Format a deadline record for display."""
    days = deadline.get("days_until", 0)

    if days < 0:
        emoji = "🔴"
        time_str = f"{abs(days)} Tage überfällig"
    elif days <= 7:
        emoji = "🟠"
        time_str = f"in {days} Tagen"
    elif days <= 14:
        emoji = "🟡"
        time_str = f"in {days} Tagen"
    else:
        emoji = "🟢"
        time_str = f"in {days} Tagen"

    deadline_type = {
        "termination_notice": "Kündigungsfrist",
        "auto_renewal": "Auto-Verlängerung",
        "payment_due": "Zahlung fällig",
        "contract_end": "Vertragsende",
        "review": "Review-Termin",
    }.get(deadline.get("deadline_type", ""), deadline.get("deadline_type", "Frist"))

    lines = [
        f"{emoji} **{deadline_type}** ({time_str})",
        f"   Vertrag: {deadline.get('contract_filename', 'Unbekannt')}",
        f"   Datum: {deadline.get('deadline_date', '')}",
    ]

    if deadline.get("source_clause"):
        lines.append(f'   Quelle: "{deadline["source_clause"][:100]}..."')

    return "\n".join(lines)


async def search_contracts(
    ctx: DbToolContext,
    query: str,
    contract_type: str | None = None,
    limit: int = 10,
) -> str:
    """Search contracts by keyword.

    Uses PostgreSQL full-text search on contract content and filenames.

    Args:
        query: Search terms
        contract_type: Optional filter by type
        limit: Maximum results
    Returns:
        Formatted list of matching contracts
    """
    org_id = ctx.organization_id

    try:
        async with ctx.session_factory() as session:
            # Build query with full-text search
            # Using to_tsvector and to_tsquery for PostgreSQL FTS
            sql = text("""
                SELECT
                    c.id,
                    c.filename,
                    c.contract_type,
                    c.status,
                    c.created_at,
                    a.risk_score,
                    a.summary
                FROM contracts c
                LEFT JOIN contract_analyses a ON c.id = a.contract_id
                WHERE c.organization_id = :org_id
                  AND c.deleted_at IS NULL
                  AND (
                      c.filename ILIKE :pattern
                      OR c.raw_text ILIKE :pattern
                      OR a.summary ILIKE :pattern
                  )
                ORDER BY c.created_at DESC
                LIMIT :limit
            """)

            pattern = f"%{query}%"
            result = await session.execute(
                sql,
                {"org_id": str(org_id), "pattern": pattern, "limit": limit},
            )
            contracts = [dict(row._mapping) for row in result.fetchall()]

            if not contracts:
                return f"Keine Verträge gefunden für: {query}"

            output = [
                f"# Vertragssuche: {query}",
                "",
                f"Gefunden: {len(contracts)} Verträge",
                "",
            ]

            for c in contracts:
                output.append(_format_contract(c))
                output.append("")

            return "\n".join(output)

    except Exception as e:
        logger.exception("Error searching contracts")
        return f"Fehler bei der Vertragssuche: {str(e)}"


async def get_contract(
    ctx: DbToolContext,
    contract_id: str,
) -> str:
    """Get full details of a specific contract.

    Args:
        contract_id: UUID of the contract
    Returns:
        Full contract details including analysis
    """
    org_id = ctx.organization_id

    try:
        contract_uuid = UUID(contract_id)
    except ValueError:
        return f"Ungültige Vertrags-ID: {contract_id}"

    try:
        async with ctx.session_factory() as session:
            # Get contract with analysis
            sql = text("""
                SELECT
                    c.id,
                    c.filename,
                    c.file_type,
                    c.contract_type,
                    c.status,
                    c.raw_text,
                    c.page_count,
                    c.created_at,
                    a.risk_score,
                    a.summary,
                    a.key_dates,
                    a.parties,
                    a.recommendations
                FROM contracts c
                LEFT JOIN contract_analyses a ON c.id = a.contract_id
                WHERE c.id = :contract_id
                  AND c.organization_id = :org_id
                  AND c.deleted_at IS NULL
            """)

            result = await session.execute(
                sql,
                {"contract_id": str(contract_uuid), "org_id": str(org_id)},
            )
            row = result.fetchone()

            if row is None:
                return f"Vertrag nicht gefunden: {contract_id}"

            c = dict(row._mapping)

            # Get findings
            findings_sql = text("""
                SELECT
                    f.finding_type,
                    f.severity,
                    f.title,
                    f.description,
                    f.clause_text,
                    f.recommendation
                FROM contract_findings f
                JOIN contract_analyses a ON f.analysis_id = a.id
                WHERE a.contract_id = :contract_id
                  AND a.organization_id = :org_id
                ORDER BY
                    CASE f.severity
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END
            """)

            findings_result = await session.execute(
                findings_sql,
                {"contract_id": str(contract_uuid), "org_id": str(org_id)},
            )
            findings = [dict(row._mapping) for row in findings_result.fetchall()]

            # Format output
            output = [
                f"# {c['filename']}",
                "",
                f"**Typ:** {c.get('contract_type', 'Unbekannt')}",
                f"**Status:** {c.get('status', '')}",
                f"**Seiten:** {c.get('page_count', 'Unbekannt')}",
                f"**Hochgeladen:** {c.get('created_at', '')}",
            ]

            if c.get("risk_score") is not None:
                score = c["risk_score"]
                emoji = "🟢" if score < 30 else "🟡" if score < 60 else "🟠" if score < 80 else "🔴"
                output.append(f"**Risiko:** {emoji} {score}/100")

            if c.get("summary"):
                output.append("")
                output.append("## Zusammenfassung")
                output.append(c["summary"])

            if c.get("parties"):
                output.append("")
                output.append("## Parteien")
                parties = c["parties"] if isinstance(c["parties"], list) else []
                for party in parties:
                    output.append(f"- {party}")

            if findings:
                output.append("")
                output.append("## Erkenntnisse")
                for f in findings:
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(f.get("severity", ""), "⚪")

                    output.append(f"\n### {severity_emoji} {f.get('title', 'Unbekannt')}")
                    output.append(f"*{f.get('finding_type', '')} - {f.get('severity', '')}*")

                    if f.get("description"):
                        output.append(f.get("description"))

                    if f.get("clause_text"):
                        output.append(f"\n> {f['clause_text'][:300]}...")

                    if f.get("recommendation"):
                        output.append(f"\n**Empfehlung:** {f['recommendation']}")

            if c.get("recommendations"):
                output.append("")
                output.append("## Empfehlungen")
                recs = c["recommendations"] if isinstance(c["recommendations"], list) else []
                for rec in recs:
                    output.append(f"- {rec}")

            return "\n".join(output)

    except Exception as e:
        logger.exception("Error getting contract")
        return f"Fehler beim Laden des Vertrags: {str(e)}"


async def get_partners(
    ctx: DbToolContext,
    risk_level: str | None = None,
    limit: int = 20,
) -> str:
    """List all business partners with their risk scores.

    Args:
        risk_level: Filter by risk level (low, medium, high, critical)
        limit: Maximum results
    Returns:
        Formatted list of partners
    """
    org_id = ctx.organization_id

    try:
        async with ctx.session_factory() as session:
            sql = text("""
                SELECT
                    id,
                    name,
                    partner_type,
                    risk_level,
                    risk_score,
                    registration_number,
                    country,
                    is_watched,
                    created_at
                FROM partners
                WHERE organization_id = :org_id
                  AND deleted_at IS NULL
                  AND (:risk_level IS NULL OR risk_level = :risk_level)
                ORDER BY
                    CASE risk_level
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    name
                LIMIT :limit
            """)

            result = await session.execute(
                sql,
                {"org_id": str(org_id), "risk_level": risk_level, "limit": limit},
            )
            partners = [dict(row._mapping) for row in result.fetchall()]

            if not partners:
                return "Keine Partner gefunden."

            output = [
                "# Geschäftspartner",
                "",
                f"Gefunden: {len(partners)} Partner",
            ]

            if risk_level:
                output.append(f"Filter: Risiko = {risk_level}")

            output.append("")

            for p in partners:
                output.append(_format_partner(p))
                output.append("")

            return "\n".join(output)

    except Exception as e:
        logger.exception("Error getting partners")
        return f"Fehler beim Laden der Partner: {str(e)}"


async def get_deadlines(
    ctx: DbToolContext,
    days_ahead: int = 30,
    include_overdue: bool = True,
) -> str:
    """Get upcoming deadlines from contracts.

    Args:
        days_ahead: How many days to look ahead
        include_overdue: Include overdue deadlines
    Returns:
        Formatted list of deadlines
    """
    org_id = ctx.organization_id

    try:
        async with ctx.session_factory() as session:
            today = date.today()
            end_date = today + timedelta(days=days_ahead)

            # Note: This assumes a deadlines table exists
            # If not, we need to extract from contract analyses
            sql = text("""
                SELECT
                    d.id,
                    d.deadline_type,
                    d.deadline_date,
                    d.source_clause,
                    d.is_verified,
                    d.confidence,
                    c.filename as contract_filename,
                    c.id as contract_id,
                    (d.deadline_date - CURRENT_DATE) as days_until
                FROM deadlines d
                JOIN contracts c ON d.contract_id = c.id
                WHERE d.organization_id = :org_id
                  AND d.deleted_at IS NULL
                  AND (
                      (d.deadline_date <= :end_date AND d.deadline_date >= :today)
                      OR (:include_overdue AND d.deadline_date < :today)
                  )
                ORDER BY d.deadline_date ASC
                LIMIT 50
            """)

            try:
                result = await session.execute(
                    sql,
                    {
                        "org_id": str(org_id),
                        "today": today,
                        "end_date": end_date,
                        "include_overdue": include_overdue,
                    },
                )
                deadlines = [dict(row._mapping) for row in result.fetchall()]
            except Exception:
                # If deadlines table doesn't exist, return message
                return """# Fristen

Keine Fristen-Tabelle gefunden.

Das Fristen-Feature wurde noch nicht vollständig migriert.
Bitte prüfen Sie die Verträge einzeln auf Fristen.

*Hinweis: Die Fristen-Extraktion erfolgt bei der Vertragsanalyse.*"""

            if not deadlines:
                return f"""# Fristen (nächste {days_ahead} Tage)

✅ Keine anstehenden Fristen.

Es wurden keine Fristen in den nächsten {days_ahead} Tagen gefunden.
{'Auch keine überfälligen Fristen vorhanden.' if include_overdue else ''}"""

            # Count overdue
            overdue_count = sum(1 for d in deadlines if d.get("days_until", 0) < 0)

            output = [
                f"# Fristen (nächste {days_ahead} Tage)",
                "",
            ]

            if overdue_count > 0:
                output.append(f"⚠️ **{overdue_count} überfällige Fristen!**")
                output.append("")

            output.append(f"Gefunden: {len(deadlines)} Fristen")
            output.append("")

            # Group by urgency
            overdue = [d for d in deadlines if d.get("days_until", 0) < 0]
            urgent = [d for d in deadlines if 0 <= d.get("days_until", 0) <= 7]
            upcoming = [d for d in deadlines if 7 < d.get("days_until", 0) <= 30]
            later = [d for d in deadlines if d.get("days_until", 0) > 30]

            if overdue:
                output.append("## 🔴 Überfällig")
                for d in overdue:
                    output.append(_format_deadline(d))
                output.append("")

            if urgent:
                output.append("## 🟠 Diese Woche")
                for d in urgent:
                    output.append(_format_deadline(d))
                output.append("")

            if upcoming:
                output.append("## 🟡 Nächste 30 Tage")
                for d in upcoming:
                    output.append(_format_deadline(d))
                output.append("")

            if later:
                output.append("## 🟢 Später")
                for d in later:
                    output.append(_format_deadline(d))

            return "\n".join(output)

    except Exception as e:
        logger.exception("Error getting deadlines")
        return f"Fehler beim Laden der Fristen: {str(e)}"
