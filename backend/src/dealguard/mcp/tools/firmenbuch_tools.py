"""MCP Tools for Austrian Firmenbuch (Company Registry).

These tools provide Claude with access to Austrian company data
via OpenFirmenbuch (free) and other sources.
"""

import json
import logging
from typing import Any

from dealguard.infrastructure.external.openfirmenbuch import (
    OpenFirmenbuchProvider,
    FallbackFirmenbuchProvider,
)

logger = logging.getLogger(__name__)


async def search_firmenbuch(
    query: str,
    limit: int = 5,
) -> str:
    """Durchsucht das österreichische Firmenbuch nach Unternehmen.

    Verwende dieses Tool um österreichische Unternehmen zu finden.
    Es liefert grundlegende Firmendaten wie:
    - Firmenwortlaut (offizieller Name)
    - Firmenbuchnummer (FN)
    - Rechtsform (GmbH, AG, KG, etc.)
    - Sitz (Standort)

    Args:
        query: Firmenname oder Teil davon (z.B. "Red Bull", "OMV")
        limit: Maximale Anzahl Ergebnisse (Standard: 5)

    Returns:
        JSON mit gefundenen Unternehmen oder Fehlermeldung
    """
    try:
        provider = OpenFirmenbuchProvider()

        results = await provider.search_companies(
            query=query,
            country="AT",
            limit=limit,
        )

        await provider.close()

        if not results:
            return json.dumps({
                "status": "no_results",
                "message": f"Keine Unternehmen für '{query}' gefunden.",
                "query": query,
            }, ensure_ascii=False)

        companies = []
        for r in results:
            companies.append({
                "firmenbuchnummer": r.handelsregister_id,
                "name": r.name,
                "rechtsform": r.legal_form,
                "sitz": r.city,
                "status": r.status,
            })

        return json.dumps({
            "status": "ok",
            "count": len(companies),
            "companies": companies,
            "source": "OpenFirmenbuch",
        }, ensure_ascii=False)

    except Exception as e:
        logger.exception(f"Firmenbuch search error: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Fehler bei der Firmenbuch-Suche: {str(e)}",
        }, ensure_ascii=False)


async def get_firmenbuch_auszug(
    firmenbuchnummer: str,
) -> str:
    """Holt detaillierte Firmendaten aus dem Firmenbuch.

    Verwende dieses Tool um vollständige Informationen zu einem
    österreichischen Unternehmen abzurufen, wenn du die Firmenbuchnummer
    bereits kennst (z.B. aus einer vorherigen Suche).

    Die Daten umfassen (soweit verfügbar):
    - Vollständiger Firmenwortlaut
    - Geschäftsführer/Vorstand
    - Stammkapital
    - Unternehmensgegenstand
    - Firmenbuchgericht
    - Eintragungsdatum

    Args:
        firmenbuchnummer: Die FN-Nummer (z.B. "123456a" oder "FN 123456a")

    Returns:
        JSON mit Firmendaten oder Fehlermeldung
    """
    try:
        provider = OpenFirmenbuchProvider()

        company = await provider.search_by_fn(firmenbuchnummer)

        await provider.close()

        if not company:
            return json.dumps({
                "status": "not_found",
                "message": f"Kein Unternehmen mit FN '{firmenbuchnummer}' gefunden.",
                "firmenbuchnummer": firmenbuchnummer,
            }, ensure_ascii=False)

        result = {
            "status": "ok",
            "firmenbuchnummer": company.handelsregister_id,
            "name": company.name,
            "rechtsform": company.legal_form,
            "firmenbuchgericht": company.registration_court,
            "eintragungsdatum": company.registration_date,
            "sitz": company.city,
            "adresse": {
                "strasse": company.street,
                "plz": company.postal_code,
                "ort": company.city,
            } if company.street else None,
            "stammkapital": f"EUR {company.share_capital:,.2f}" if company.share_capital else None,
            "geschaeftsfuehrer": company.managing_directors,
            "unternehmensgegenstand": company.business_purpose,
            "status": company.status,
            "source": "OpenFirmenbuch",
        }

        # Remove None values
        result = {k: v for k, v in result.items() if v is not None}

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.exception(f"Firmenbuch get error: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Fehler beim Abrufen der Firmendaten: {str(e)}",
        }, ensure_ascii=False)


async def check_company_austria(
    company_name: str,
) -> str:
    """Prüft ein österreichisches Unternehmen auf Existenz und liefert Basisdaten.

    Dies ist ein Convenience-Tool das:
    1. Nach dem Unternehmen sucht
    2. Das beste Ergebnis zurückliefert
    3. Grundlegende Daten anzeigt

    Ideal für schnelle Firmenprüfungen im Rahmen von Partner-Checks.

    Args:
        company_name: Name des zu prüfenden Unternehmens

    Returns:
        JSON mit Firmendaten oder Status "nicht gefunden"
    """
    try:
        provider = OpenFirmenbuchProvider()

        # Search for company
        results = await provider.search_companies(
            query=company_name,
            country="AT",
            limit=3,
        )

        if not results:
            await provider.close()
            return json.dumps({
                "status": "not_found",
                "message": f"Unternehmen '{company_name}' nicht im Firmenbuch gefunden.",
                "hinweis": "Das Unternehmen könnte unter einem anderen Namen eingetragen sein, "
                          "nicht in Österreich registriert sein, oder ein Einzelunternehmen ohne "
                          "Firmenbuch-Eintrag sein.",
            }, ensure_ascii=False)

        # Get best match
        best_match = results[0]

        # Try to get full details
        company = await provider.get_company_data(best_match.provider_id)
        await provider.close()

        if company:
            result = {
                "status": "found",
                "firmenbuchnummer": company.handelsregister_id,
                "name": company.name,
                "rechtsform": company.legal_form,
                "sitz": company.city,
                "status": company.status,
                "geschaeftsfuehrer": company.managing_directors,
                "stammkapital": f"EUR {company.share_capital:,.2f}" if company.share_capital else None,
                "source": "OpenFirmenbuch",
                "weitere_treffer": len(results) - 1 if len(results) > 1 else 0,
            }
        else:
            result = {
                "status": "found",
                "firmenbuchnummer": best_match.handelsregister_id,
                "name": best_match.name,
                "rechtsform": best_match.legal_form,
                "sitz": best_match.city,
                "status": best_match.status,
                "source": "OpenFirmenbuch",
                "hinweis": "Detaildaten nicht verfügbar",
            }

        # Remove None values
        result = {k: v for k, v in result.items() if v is not None}

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.exception(f"Company check error: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Fehler bei der Firmenprüfung: {str(e)}",
        }, ensure_ascii=False)


# Tool definitions for MCP
FIRMENBUCH_TOOLS = [
    {
        "name": "search_firmenbuch",
        "description": "Durchsucht das österreichische Firmenbuch nach Unternehmen. "
                      "Liefert Firmenwortlaut, FN-Nummer, Rechtsform und Sitz. "
                      "Verwende dieses Tool für Unternehmensrecherchen in Österreich.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Firmenname oder Teil davon (z.B. 'Red Bull', 'OMV')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximale Anzahl Ergebnisse",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_firmenbuch_auszug",
        "description": "Holt detaillierte Firmendaten aus dem Firmenbuch anhand der FN-Nummer. "
                      "Liefert Geschäftsführer, Stammkapital, Unternehmensgegenstand, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "firmenbuchnummer": {
                    "type": "string",
                    "description": "Firmenbuchnummer (z.B. '123456a' oder 'FN 123456a')",
                },
            },
            "required": ["firmenbuchnummer"],
        },
    },
    {
        "name": "check_company_austria",
        "description": "Schnelle Prüfung eines österreichischen Unternehmens. "
                      "Sucht nach dem Namen und liefert Basisdaten des besten Treffers. "
                      "Ideal für Partner-Checks und Due Diligence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name des zu prüfenden Unternehmens",
                },
            },
            "required": ["company_name"],
        },
    },
]
