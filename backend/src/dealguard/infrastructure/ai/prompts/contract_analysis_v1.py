"""Contract analysis prompt v1 - Austrian law focus."""

import json
from dataclasses import dataclass
from typing import Any

from dealguard.infrastructure.database.models.contract import (
    FindingCategory,
    FindingSeverity,
    RiskLevel,
)


@dataclass
class PromptVersion:
    """Prompt version metadata."""

    version: str
    name: str
    description: str


@dataclass
class ContractFindingData:
    """Parsed finding from AI response."""

    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    original_clause_text: str | None
    clause_location: dict | None
    suggested_change: str | None
    market_comparison: str | None


@dataclass
class ContractAnalysisResult:
    """Parsed analysis result from AI response."""

    risk_score: int
    risk_level: RiskLevel
    summary: str
    findings: list[ContractFindingData]
    recommendations: list[str]
    contract_type_detected: str | None


class ContractAnalysisPromptV1:
    """Contract analysis prompt for Austrian business law.

    This prompt instructs Claude to:
    1. Identify the contract type
    2. Analyze for specific risk categories
    3. Score risks and provide recommendations
    4. Output structured JSON for parsing
    """

    version = PromptVersion(
        version="1.1.0",
        name="contract_analysis",
        description="Austrian contract analysis with ABGB/UGB focus",
    )

    def render_system(self) -> str:
        """Render the system prompt."""
        return """Du bist ein erfahrener österreichischer Wirtschaftsanwalt und Vertragsanalyst.
Deine Aufgabe ist es, Verträge für KMU (kleine und mittlere Unternehmen) auf Risiken zu prüfen.

DEIN FOKUS:
- Du analysierst nach österreichischem Recht (ABGB, UGB, KSchG)
- Du berücksichtigst auch EU-Recht wo relevant (DSGVO, Verbraucherschutz)
- Du identifizierst versteckte Risiken und unfaire Klauseln
- Du gibst praktische, verständliche Empfehlungen
- Du vergleichst mit marktüblichen Standards in Österreich

RECHTLICHER KONTEXT (Österreich):
- ABGB: Allgemeines Bürgerliches Gesetzbuch (allgemeines Vertragsrecht)
- UGB: Unternehmensgesetzbuch (unternehmerischer Geschäftsverkehr)
- KSchG: Konsumentenschutzgesetz (bei B2C-Verträgen)
- MRG: Mietrechtsgesetz (bei Mietverträgen)
- DSGVO/DSG: Datenschutz

RISIKOKATEGORIEN die du prüfen MUSST:
1. HAFTUNG (liability): Unbeschränkte Haftung, einseitige Freistellung, Vertragsstrafen (beachte §879 ABGB - Sittenwidrigkeit)
2. ZAHLUNG (payment): Zahlungsziele >60 Tage, hohe Vorauszahlung, versteckte Kosten (beachte Zahlungsverzugsgesetz)
3. KÜNDIGUNG (termination): Auto-Renewal, lange Kündigungsfristen, Strafzahlungen (beachte §§1116-1117 ABGB)
4. GERICHTSSTAND (jurisdiction): Ausländisches Recht, Schiedsklauseln (beachte EU-Gerichtsstandsverordnung)
5. IP/NUTZUNGSRECHTE (ip): Vollständige Übertragung, kein Rückfall (beachte UrhG)
6. GEHEIMHALTUNG (confidentiality): Unbefristete NDA, einseitige Verpflichtung
7. DATENSCHUTZ (gdpr): Fehlende AVV, keine Löschpflichten, Drittlandübermittlung (DSGVO + DSG)
8. GEWÄHRLEISTUNG (warranty): Ausschluss, verkürzte Fristen (beachte §§922ff ABGB, KSchG bei Verbrauchern)

BEWERTUNGSSKALA:
- 0-30: Geringes Risiko (grün) - Vertrag ist fair und marktüblich
- 31-60: Moderates Risiko (gelb) - Einige Punkte sollten geprüft werden
- 61-80: Hohes Risiko (orange) - Signifikante Probleme, Verhandlung empfohlen
- 81-100: Kritisches Risiko (rot) - Nicht unterschreiben ohne wesentliche Änderungen

WICHTIG:
- Sei präzise und zitiere problematische Textpassagen
- Gib konkrete Änderungsvorschläge
- Erkläre Risiken in verständlichem Deutsch (kein Juristendeutsch)
- Vergleiche mit marktüblichen Standards in Österreich
- Verweise auf konkrete österreichische Gesetzesgrundlagen wo relevant"""

    def render_user(
        self,
        contract_text: str,
        contract_type: str | None = None,
    ) -> str:
        """Render the user prompt with contract text."""
        type_hint = ""
        if contract_type:
            type_hint = f"\nHINWEIS: Der Nutzer hat angegeben, dass es sich um einen '{contract_type}'-Vertrag handelt.\n"

        return f"""Analysiere den folgenden Vertrag und gib deine Analyse im JSON-Format zurück.
{type_hint}
VERTRAG:
---
{contract_text}
---

Antworte NUR mit validem JSON im folgenden Format:
{{
    "contract_type_detected": "supplier|customer|service|nda|lease|employment|license|other",
    "risk_score": <0-100>,
    "risk_level": "low|medium|high|critical",
    "summary": "Kurze Zusammenfassung der wichtigsten Erkenntnisse (2-3 Sätze)",
    "findings": [
        {{
            "category": "liability|payment|termination|jurisdiction|ip|confidentiality|gdpr|warranty|other",
            "severity": "info|low|medium|high|critical",
            "title": "Kurzer Titel des Problems",
            "description": "Detaillierte Erklärung warum dies problematisch ist",
            "original_clause_text": "Exaktes Zitat der problematischen Klausel",
            "clause_location": {{"page": 1, "paragraph": "§3 Abs. 2"}},
            "suggested_change": "Konkreter Formulierungsvorschlag",
            "market_comparison": "Vergleich mit marktüblichen Regelungen"
        }}
    ],
    "recommendations": [
        "Konkrete Handlungsempfehlung 1",
        "Konkrete Handlungsempfehlung 2"
    ]
}}

WICHTIG:
- Analysiere ALLE relevanten Klauseln
- Priorisiere die schwerwiegendsten Probleme
- Gib mindestens 3 Empfehlungen
- Bei geringem Risiko kannst du auch positive Aspekte erwähnen"""

    def parse_response(self, response: str) -> ContractAnalysisResult:
        """Parse AI response JSON into structured result."""
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remove first and last line
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            data = json.loads(cleaned)

            # Parse findings
            findings = []
            for f in data.get("findings", []):
                finding = ContractFindingData(
                    category=self._parse_category(f.get("category", "other")),
                    severity=self._parse_severity(f.get("severity", "medium")),
                    title=f.get("title", "Unbekanntes Problem"),
                    description=f.get("description", ""),
                    original_clause_text=f.get("original_clause_text"),
                    clause_location=f.get("clause_location"),
                    suggested_change=f.get("suggested_change"),
                    market_comparison=f.get("market_comparison"),
                )
                findings.append(finding)

            # Parse risk level
            risk_score = max(0, min(100, int(data.get("risk_score", 50))))
            risk_level = self._parse_risk_level(data.get("risk_level", "medium"))

            return ContractAnalysisResult(
                risk_score=risk_score,
                risk_level=risk_level,
                summary=data.get("summary", "Keine Zusammenfassung verfügbar"),
                findings=findings,
                recommendations=data.get("recommendations", []),
                contract_type_detected=data.get("contract_type_detected"),
            )

        except json.JSONDecodeError as e:
            # If parsing fails, create a minimal result
            from dealguard.shared.logging import get_logger

            logger = get_logger(__name__)
            logger.error("ai_response_parse_failed", error=str(e), response=response[:500])

            return ContractAnalysisResult(
                risk_score=50,
                risk_level=RiskLevel.MEDIUM,
                summary="Analyse konnte nicht vollständig geparst werden. Bitte manuell prüfen.",
                findings=[],
                recommendations=["Bitte lassen Sie den Vertrag manuell prüfen."],
                contract_type_detected=None,
            )

    def _parse_category(self, value: str) -> FindingCategory:
        """Parse category string to enum."""
        mapping = {
            "liability": FindingCategory.LIABILITY,
            "payment": FindingCategory.PAYMENT,
            "termination": FindingCategory.TERMINATION,
            "jurisdiction": FindingCategory.JURISDICTION,
            "ip": FindingCategory.IP,
            "confidentiality": FindingCategory.CONFIDENTIALITY,
            "gdpr": FindingCategory.GDPR,
            "warranty": FindingCategory.WARRANTY,
            "force_majeure": FindingCategory.FORCE_MAJEURE,
        }
        return mapping.get(value.lower(), FindingCategory.OTHER)

    def _parse_severity(self, value: str) -> FindingSeverity:
        """Parse severity string to enum."""
        mapping = {
            "info": FindingSeverity.INFO,
            "low": FindingSeverity.LOW,
            "medium": FindingSeverity.MEDIUM,
            "high": FindingSeverity.HIGH,
            "critical": FindingSeverity.CRITICAL,
        }
        return mapping.get(value.lower(), FindingSeverity.MEDIUM)

    def _parse_risk_level(self, value: str) -> RiskLevel:
        """Parse risk level string to enum."""
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        return mapping.get(value.lower(), RiskLevel.MEDIUM)
