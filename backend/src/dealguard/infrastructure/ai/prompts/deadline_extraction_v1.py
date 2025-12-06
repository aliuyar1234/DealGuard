"""Deadline extraction prompt v1 - Extract dates and deadlines from contracts.

This prompt is designed to:
1. Find ALL dates and deadlines in a contract
2. Classify them by type (termination, renewal, payment, etc.)
3. Calculate actual dates from relative terms ("3 Monate vor Ablauf")
4. Return structured JSON for database storage
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from dealguard.infrastructure.ai.prompts.contract_analysis_v1 import PromptVersion
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedDeadline:
    """A deadline extracted from a contract."""

    deadline_type: str  # termination_notice, auto_renewal, payment_due, etc.
    deadline_date: str  # ISO format YYYY-MM-DD
    description: str  # Human-readable description
    source_clause: str  # Original text from contract
    clause_location: dict | None  # {page, paragraph}
    confidence: float  # 0.0 - 1.0
    reminder_days: int  # Suggested reminder days before deadline
    is_recurring: bool  # Whether this repeats
    recurrence_pattern: str | None  # "yearly", "quarterly", "monthly"
    notes: str | None  # Additional context


@dataclass
class DeadlineExtractionResult:
    """Result from deadline extraction."""

    deadlines: list[ExtractedDeadline]
    contract_start_date: str | None
    contract_end_date: str | None
    has_auto_renewal: bool
    auto_renewal_period: str | None  # "1 Jahr", "6 Monate"
    termination_notice_period: str | None  # "3 Monate zum Quartalsende"
    warnings: list[str]  # Any issues found during extraction


class DeadlineExtractionPromptV1:
    """Extract deadlines and important dates from contracts.

    This prompt identifies:
    - Vertragslaufzeit (contract duration)
    - Kündigungsfristen (termination notice periods)
    - Automatische Verlängerung (auto-renewal)
    - Zahlungsfristen (payment terms)
    - Gewährleistungsfristen (warranty periods)
    - Preisanpassungen (price adjustments)
    - Überprüfungstermine (review dates)
    """

    version = PromptVersion(
        version="1.0.0",
        name="deadline_extraction",
        description="Extract dates and deadlines from contracts",
    )

    def render_system(self) -> str:
        """Render the system prompt."""
        return """Du bist ein Experte für Vertragsanalyse, spezialisiert auf das Extrahieren von Fristen und Terminen aus Verträgen.

DEINE AUFGABE:
Analysiere den Vertrag und extrahiere ALLE wichtigen Fristen, Termine und Deadlines.

DEADLINE-TYPEN die du suchen MUSST:
1. **termination_notice** - Kündigungsfrist
   - "kann mit einer Frist von 3 Monaten gekündigt werden"
   - "Kündigung zum Quartalsende"

2. **auto_renewal** - Automatische Verlängerung
   - "verlängert sich automatisch um ein weiteres Jahr"
   - "stillschweigende Verlängerung"

3. **contract_end** - Vertragsende
   - Festes Enddatum
   - "befristet bis zum..."

4. **payment_due** - Zahlungsfrist
   - "Zahlung innerhalb von 30 Tagen"
   - "fällig zum 15. des Monats"

5. **warranty_end** - Gewährleistungsende
   - "Gewährleistungsfrist von 24 Monaten"

6. **price_adjustment** - Preisanpassung
   - "jährliche Preisanpassung zum 01.01."
   - "Indexanpassung"

7. **review_date** - Überprüfungstermin
   - "jährliche Überprüfung"
   - "Audit-Termin"

8. **notice_period** - Sonstige Ankündigungsfrist
   - "mit 14 Tagen Vorlauf"

WICHTIGE REGELN:
1. Berechne konkrete Daten wenn möglich
   - Heute ist {today}
   - "3 Monate vor Vertragsende" → konkretes Datum berechnen
   - Bei unbekanntem Vertragsbeginn: Annahme = heute

2. Bei wiederkehrenden Fristen: Nächsten Termin berechnen
   - "zum Quartalsende" → nächstes Quartalsende

3. Zitiere IMMER die Original-Klausel
   - Exaktes Zitat aus dem Vertrag

4. Confidence-Score:
   - 1.0: Explizites Datum im Vertrag
   - 0.8: Berechnet aus klarer Formulierung
   - 0.6: Interpretation nötig
   - 0.4: Unsicher, sollte geprüft werden

5. Empfehle sinnvolle Erinnerungszeiten
   - Kündigungsfristen: 30-60 Tage vorher
   - Zahlungen: 7-14 Tage vorher
   - Auto-Renewal: 60-90 Tage vorher"""

    def render_user(
        self,
        contract_text: str,
        contract_filename: str,
        reference_date: date | None = None,
    ) -> str:
        """Render the user prompt with contract text."""
        today = reference_date or date.today()

        return f"""Analysiere diesen Vertrag und extrahiere alle Fristen und Termine.

DATEINAME: {contract_filename}
HEUTIGES DATUM: {today.isoformat()}

═══════════════════════════════════════════════════════════════
                         VERTRAGSTEXT
═══════════════════════════════════════════════════════════════

{contract_text}

═══════════════════════════════════════════════════════════════

Antworte NUR mit validem JSON im folgenden Format:
{{
    "contract_start_date": "YYYY-MM-DD oder null",
    "contract_end_date": "YYYY-MM-DD oder null",
    "has_auto_renewal": true/false,
    "auto_renewal_period": "1 Jahr" oder null,
    "termination_notice_period": "3 Monate zum Quartalsende" oder null,
    "deadlines": [
        {{
            "deadline_type": "termination_notice|auto_renewal|contract_end|payment_due|warranty_end|price_adjustment|review_date|notice_period|other",
            "deadline_date": "YYYY-MM-DD",
            "description": "Kurze Beschreibung der Frist",
            "source_clause": "Exaktes Zitat aus dem Vertrag",
            "clause_location": {{"page": 1, "paragraph": "§5 Abs. 2"}},
            "confidence": 0.8,
            "reminder_days": 30,
            "is_recurring": false,
            "recurrence_pattern": null,
            "notes": "Zusätzliche Hinweise"
        }}
    ],
    "warnings": [
        "Warnung wenn etwas unklar ist"
    ]
}}

WICHTIG:
- Finde ALLE relevanten Fristen
- Berechne konkrete Daten
- Zitiere Original-Klauseln
- Bei Unklarheit: niedrigere Confidence + Warnung"""

    def parse_response(self, response: str) -> DeadlineExtractionResult:
        """Parse AI response JSON into structured result."""
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            data = json.loads(cleaned)

            # Parse deadlines
            deadlines = []
            for d in data.get("deadlines", []):
                deadline = ExtractedDeadline(
                    deadline_type=d.get("deadline_type", "other"),
                    deadline_date=d.get("deadline_date", ""),
                    description=d.get("description", ""),
                    source_clause=d.get("source_clause", ""),
                    clause_location=d.get("clause_location"),
                    confidence=float(d.get("confidence", 0.5)),
                    reminder_days=int(d.get("reminder_days", 30)),
                    is_recurring=bool(d.get("is_recurring", False)),
                    recurrence_pattern=d.get("recurrence_pattern"),
                    notes=d.get("notes"),
                )
                deadlines.append(deadline)

            return DeadlineExtractionResult(
                deadlines=deadlines,
                contract_start_date=data.get("contract_start_date"),
                contract_end_date=data.get("contract_end_date"),
                has_auto_renewal=bool(data.get("has_auto_renewal", False)),
                auto_renewal_period=data.get("auto_renewal_period"),
                termination_notice_period=data.get("termination_notice_period"),
                warnings=data.get("warnings", []),
            )

        except json.JSONDecodeError as e:
            logger.error(
                "deadline_extraction_parse_failed",
                error=str(e),
                response=response[:500],
            )

            return DeadlineExtractionResult(
                deadlines=[],
                contract_start_date=None,
                contract_end_date=None,
                has_auto_renewal=False,
                auto_renewal_period=None,
                termination_notice_period=None,
                warnings=["Parsing fehlgeschlagen - manuelle Prüfung erforderlich"],
            )
