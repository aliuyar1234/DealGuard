"""Shared helpers for MCP v2 tool implementations."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

CHARACTER_LIMIT = 25000  # Maximum response size in characters


def truncate_response(result: str, item_count: int = 0) -> str:
    """Truncate response if it exceeds CHARACTER_LIMIT."""
    if len(result) <= CHARACTER_LIMIT:
        return result

    truncated = result[: CHARACTER_LIMIT - 500]
    truncation_msg = (
        f"\n\n---\n**Hinweis:** Antwort gekürzt (von {len(result)} auf {CHARACTER_LIMIT} Zeichen). "
    )
    if item_count > 0:
        truncation_msg += "Verwende 'offset' Parameter oder Filter für weitere Ergebnisse."
    return truncated + truncation_msg


def format_pagination_info(total: int, count: int, offset: int, limit: int) -> dict[str, Any]:
    """Generate standard pagination metadata."""
    return {
        "total": total,
        "count": count,
        "offset": offset,
        "limit": limit,
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
    if "connection" in str(e).lower():
        return (
            f"Fehler bei {context}: Verbindung fehlgeschlagen. "
            "Der externe Dienst ist möglicherweise nicht erreichbar."
        )
    if "not found" in str(e).lower() or "404" in str(e):
        return f"Fehler bei {context}: Ressource nicht gefunden. Prüfe die ID/Nummer."

    logger.exception("Error in %s", context)
    return f"Fehler bei {context}: {error_type} - {str(e)}"
