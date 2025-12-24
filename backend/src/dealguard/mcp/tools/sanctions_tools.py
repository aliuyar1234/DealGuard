"""MCP Tools for Sanctions and PEP Screening.

These tools provide Claude with access to sanctions lists
and PEP (Politically Exposed Persons) data via OpenSanctions.
"""

import json
import logging
from typing import Any

from dealguard.infrastructure.external.opensanctions import (
    OpenSanctionsProvider,
    PEPScreeningProvider,
)

logger = logging.getLogger(__name__)


async def check_sanctions(
    name: str,
    country: str = "AT",
    aliases: list[str] | None = None,
) -> str:
    """Prüft ob ein Unternehmen oder eine Person auf Sanktionslisten steht.

    Durchsucht internationale Sanktionslisten nach dem angegebenen Namen:
    - EU Sanktionslisten (CFSP)
    - UN Consolidated Sanctions
    - US OFAC SDN List
    - UK HMT Sanctions
    - Schweizer SECO Liste
    - Weitere internationale Listen

    WICHTIG: Bei Treffern mit hoher Übereinstimmung (Score >= 0.8) sollte
    KEINE Geschäftsbeziehung eingegangen werden ohne rechtliche Klärung!

    Args:
        name: Name des Unternehmens oder der Person
        country: Ländercode für Kontext (z.B. "AT", "DE")
        aliases: Alternative Namen die ebenfalls geprüft werden sollen

    Returns:
        JSON mit Sanktionsprüfungs-Ergebnis
    """
    try:
        provider = OpenSanctionsProvider()

        result = await provider.check_sanctions(
            company_name=name,
            country=country,
            aliases=aliases,
        )

        await provider.close()

        response: dict[str, Any] = {
            "status": "ok",
            "name_geprueft": name,
            "ist_sanktioniert": result.is_sanctioned,
            "risiko_score": result.score,
            "geprufte_listen": result.lists_checked,
            "zusammenfassung": result.summary,
        }

        if result.matches:
            response["treffer"] = [
                {
                    "name": match.get("name"),
                    "typ": match.get("schema"),  # Person, Company, etc.
                    "uebereinstimmung": f"{match.get('score', 0) * 100:.0f}%",
                    "listen": match.get("datasets", []),
                    "laender": match.get("countries", []),
                }
                for match in result.matches[:5]
            ]

        if result.is_sanctioned:
            response["warnung"] = (
                "⚠️ ACHTUNG: Diese Entität steht auf einer oder mehreren Sanktionslisten! "
                "Geschäftsbeziehungen könnten gegen EU/US-Sanktionsrecht verstoßen. "
                "Bitte rechtliche Beratung einholen!"
            )

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"Sanctions check error: {e}")
        return json.dumps(
            {
                "status": "error",
                "message": f"Fehler bei der Sanktionsprüfung: {str(e)}",
                "hinweis": "Die Sanktionsprüfung konnte nicht durchgeführt werden. "
                "Bitte manuell prüfen oder später erneut versuchen.",
            },
            ensure_ascii=False,
        )


async def check_pep(
    person_name: str,
    country: str = "AT",
) -> str:
    """Prüft ob eine Person ein PEP (Politically Exposed Person) ist.

    PEPs sind Personen in öffentlichen Ämtern oder mit politischem Einfluss.
    Die Prüfung ist wichtig für:
    - KYC (Know Your Customer) Compliance
    - Geldwäsche-Prävention (AML)
    - Due Diligence bei Geschäftspartnern

    Durchsucht werden:
    - Nationale und internationale Politikerdatenbanken
    - Beamte in Schlüsselpositionen
    - Familienangehörige und nahestehende Personen von PEPs

    Args:
        person_name: Vollständiger Name der Person
        country: Ländercode für Kontext (z.B. "AT" für Österreich)

    Returns:
        JSON mit PEP-Prüfungs-Ergebnis
    """
    try:
        provider = PEPScreeningProvider()

        result = await provider.check_pep(
            person_name=person_name,
            country=country,
        )

        await provider.close()

        response: dict[str, Any] = {
            "status": "ok",
            "name_geprueft": person_name,
            "ist_pep": result.get("is_pep", False),
            "risiko_score": result.get("score", 0),
            "zusammenfassung": result.get("summary"),
        }

        if result.get("matches"):
            response["treffer"] = [
                {
                    "name": match.get("name"),
                    "uebereinstimmung": f"{match.get('score', 0) * 100:.0f}%",
                    "themen": match.get("topics", []),
                    "laender": match.get("countries", []),
                }
                for match in result["matches"][:5]
            ]

        if result.get("is_pep"):
            response["hinweis"] = (
                "Diese Person ist möglicherweise ein PEP. "
                "Bei Geschäftsbeziehungen mit PEPs gelten erhöhte Sorgfaltspflichten "
                "gemäß EU-Geldwäscherichtlinie (AMLD). "
                "Enhanced Due Diligence (EDD) erforderlich."
            )

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"PEP check error: {e}")
        return json.dumps(
            {
                "status": "error",
                "message": f"Fehler bei der PEP-Prüfung: {str(e)}",
            },
            ensure_ascii=False,
        )


async def comprehensive_compliance_check(
    name: str,
    entity_type: str = "company",
    country: str = "AT",
) -> str:
    """Führt eine umfassende Compliance-Prüfung durch.

    Kombiniert mehrere Prüfungen in einem Aufruf:
    1. Sanktionslisten-Prüfung
    2. PEP-Prüfung (bei Personen oder Geschäftsführern)

    Ideal für:
    - Onboarding neuer Geschäftspartner
    - Jährliche Compliance-Reviews
    - Due Diligence bei Vertragsabschluss

    Args:
        name: Name des Unternehmens oder der Person
        entity_type: "company" oder "person"
        country: Ländercode (z.B. "AT")

    Returns:
        JSON mit kombiniertem Compliance-Ergebnis
    """
    try:
        sanctions_provider = OpenSanctionsProvider()

        # Always do sanctions check
        sanctions_result = await sanctions_provider.check_sanctions(
            company_name=name,
            country=country,
        )
        await sanctions_provider.close()

        # Do PEP check for persons
        pep_result = None
        if entity_type == "person":
            pep_provider = PEPScreeningProvider()
            pep_result = await pep_provider.check_pep(
                person_name=name,
                country=country,
            )
            await pep_provider.close()

        # Calculate overall risk
        risk_level = "niedrig"
        risk_score = sanctions_result.score

        if pep_result:
            risk_score = max(risk_score, pep_result.get("score", 0) * 100)

        if risk_score >= 80:
            risk_level = "kritisch"
        elif risk_score >= 50:
            risk_level = "hoch"
        elif risk_score >= 25:
            risk_level = "mittel"

        response: dict[str, Any] = {
            "status": "ok",
            "geprueft": name,
            "typ": entity_type,
            "land": country,
            "gesamtrisiko": {
                "level": risk_level,
                "score": risk_score,
            },
            "pruefungen": {
                "sanktionen": {
                    "ist_sanktioniert": sanctions_result.is_sanctioned,
                    "score": sanctions_result.score,
                    "treffer": len(sanctions_result.matches) if sanctions_result.matches else 0,
                    "zusammenfassung": sanctions_result.summary,
                },
            },
        }

        if pep_result:
            response["pruefungen"]["pep"] = {
                "ist_pep": pep_result.get("is_pep", False),
                "score": pep_result.get("score", 0),
                "treffer": len(pep_result.get("matches", [])),
                "zusammenfassung": pep_result.get("summary"),
            }

        # Add recommendations
        empfehlungen = []

        if sanctions_result.is_sanctioned:
            empfehlungen.append("🚫 KEINE Geschäftsbeziehung ohne rechtliche Klärung!")
        elif sanctions_result.matches:
            empfehlungen.append(
                "⚠️ Mögliche Treffer auf Sanktionslisten - manuelle Prüfung empfohlen"
            )

        if pep_result and pep_result.get("is_pep"):
            empfehlungen.append("📋 Enhanced Due Diligence (EDD) erforderlich (PEP)")

        if not empfehlungen:
            empfehlungen.append(
                "✅ Keine Compliance-Risiken identifiziert - Standardprüfung ausreichend"
            )

        response["empfehlungen"] = empfehlungen

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"Compliance check error: {e}")
        return json.dumps(
            {
                "status": "error",
                "message": f"Fehler bei der Compliance-Prüfung: {str(e)}",
            },
            ensure_ascii=False,
        )


# Tool definitions for MCP
SANCTIONS_TOOLS = [
    {
        "name": "check_sanctions",
        "description": "Prüft ob ein Unternehmen oder eine Person auf internationalen "
        "Sanktionslisten steht (EU, UN, US OFAC, UK, Schweiz). "
        "WICHTIG für Geschäftspartner-Prüfung und Compliance!",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name des Unternehmens oder der Person",
                },
                "country": {
                    "type": "string",
                    "description": "Ländercode (z.B. 'AT', 'DE')",
                    "default": "AT",
                },
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative Namen zum Prüfen",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "check_pep",
        "description": "Prüft ob eine Person ein PEP (Politically Exposed Person) ist. "
        "Wichtig für KYC/AML Compliance und Geldwäsche-Prävention.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": "Vollständiger Name der Person",
                },
                "country": {
                    "type": "string",
                    "description": "Ländercode für Kontext",
                    "default": "AT",
                },
            },
            "required": ["person_name"],
        },
    },
    {
        "name": "comprehensive_compliance_check",
        "description": "Umfassende Compliance-Prüfung: Sanktionen + PEP in einem Aufruf. "
        "Ideal für Onboarding neuer Geschäftspartner und Due Diligence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name des Unternehmens oder der Person",
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["company", "person"],
                    "description": "Art der Entität",
                    "default": "company",
                },
                "country": {
                    "type": "string",
                    "description": "Ländercode",
                    "default": "AT",
                },
            },
            "required": ["name"],
        },
    },
]
