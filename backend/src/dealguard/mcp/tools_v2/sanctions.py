"""Sanctions tools for MCP v2."""

from __future__ import annotations

import json

from dealguard.mcp.models import (
    CheckPEPInput,
    CheckSanctionsInput,
    ComprehensiveComplianceInput,
    ResponseFormat,
)
from dealguard.mcp.tools_v2.common import handle_error


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

            lines.extend(
                [
                    "---",
                    "**⚖️ HANDLUNGSEMPFEHLUNG:**",
                    "- Keine Geschäftsbeziehung eingehen/fortführen",
                    "- Rechtliche Beratung einholen",
                    "- Ggf. Meldepflichten prüfen (GwG)",
                ]
            )

            return "\n".join(lines)

        return (
            f"# ✅ Keine Sanktionstreffer: {params.name}\n\n"
            "Geprüfte Listen: EU, UN, US OFAC, UK HMT, CH SECO\n\n"
            "*Hinweis: Dies ist ein Screening-Tool. Für rechtlich verbindliche "
            "Prüfungen professionelle Compliance-Dienste nutzen.*"
        )

    except Exception as e:
        return handle_error(e, "Sanktionsprüfung")


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

            lines.extend(
                [
                    "---",
                    "**📋 HANDLUNGSEMPFEHLUNG (Enhanced Due Diligence):**",
                    "- Erweiterte Identitätsprüfung durchführen",
                    "- Herkunft der Mittel klären",
                    "- Geschäftsbeziehung dokumentieren",
                    "- Regelmäßige Überprüfung einrichten",
                    "- Ggf. Genehmigung der Geschäftsleitung einholen",
                ]
            )

            return "\n".join(lines)

        return (
            f"# ✅ Kein PEP: {params.person_name}\n\n"
            "Keine Treffer in PEP-Datenbanken gefunden.\n\n"
            "*Hinweis: Standard-Sorgfaltspflichten anwenden.*"
        )

    except Exception as e:
        return handle_error(e, "PEP-Prüfung")


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

        lines.append(
            f"\n### PEP-Status: {'⚠️ PEP' if result.get('is_pep') else '✅ Kein PEP'}"
        )

        if result.get("pep_matches"):
            for match in result["pep_matches"]:
                lines.append(f"- {match.get('name')}: {match.get('position')}")

        if not is_clean:
            lines.extend(
                [
                    "",
                    "---",
                    "**📋 Empfohlene Maßnahmen:**",
                    "- Detailprüfung der Treffer durchführen",
                    "- Rechtliche Beratung einholen",
                    "- Dokumentation erstellen",
                ]
            )

        return "\n".join(lines)

    except Exception as e:
        return handle_error(e, "Compliance-Prüfung")
