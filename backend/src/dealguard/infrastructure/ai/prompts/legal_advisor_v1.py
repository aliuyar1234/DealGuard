"""Legal advisor prompt v1 - Anti-hallucination focused.

This prompt is designed to:
1. Answer legal questions ONLY from provided contract context
2. Always cite sources with exact quotes
3. Refuse to speculate or hallucinate
4. Recommend lawyers when appropriate
"""

import json
from dataclasses import dataclass, field

from dealguard.infrastructure.ai.prompts.contract_analysis_v1 import PromptVersion
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Citation:
    """A citation to a specific contract clause."""

    number: int
    contract_id: str
    contract_filename: str
    clause_text: str
    page: int | None = None
    paragraph: str | None = None


@dataclass
class LegalAdvisorResponse:
    """Parsed response from the legal advisor AI."""

    answer: str
    citations: list[Citation]
    confidence: float  # 0.0 - 1.0
    requires_lawyer: bool
    follow_up_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization."""
        return {
            "answer": self.answer,
            "citations": [
                {
                    "number": c.number,
                    "contract_id": c.contract_id,
                    "contract_filename": c.contract_filename,
                    "clause_text": c.clause_text,
                    "page": c.page,
                    "paragraph": c.paragraph,
                }
                for c in self.citations
            ],
            "confidence": self.confidence,
            "requires_lawyer": self.requires_lawyer,
            "follow_up_questions": self.follow_up_questions,
        }


@dataclass
class ClauseInput:
    """Input clause for the prompt."""

    number: int
    contract_id: str
    contract_filename: str
    clause_text: str
    page: int | None = None


class LegalAdvisorPromptV1:
    """Legal advisor prompt with strong anti-hallucination measures.

    Key Features:
    1. Only answers from provided contract context
    2. Mandatory citations for every claim
    3. Structured JSON output for validation
    4. Clear "I don't know" paths
    5. Lawyer recommendation when appropriate
    """

    version = PromptVersion(
        version="1.0.0",
        name="legal_advisor",
        description="Austrian legal advisor with anti-hallucination focus",
    )

    def render_system(
        self,
        company_name: str | None = None,
        jurisdiction: str = "AT",
    ) -> str:
        """Render the system prompt.

        Args:
            company_name: Name of the company (optional)
            jurisdiction: Legal jurisdiction (AT, DE, CH)
        """
        jurisdiction_name = {
            "AT": "österreichischem",
            "DE": "deutschem",
            "CH": "schweizerischem",
        }.get(jurisdiction, "österreichischem")

        company_context = ""
        if company_name:
            company_context = f" für {company_name}"

        return f"""Du bist der Inhouse-Jurist{company_context}. Du beantwortest rechtliche Fragen basierend auf den Verträgen des Unternehmens.

═══════════════════════════════════════════════════════════════
                    KRITISCHE REGELN (ANTI-HALLUZINATION)
═══════════════════════════════════════════════════════════════

1. QUELLENPFLICHT: Du darfst NUR Informationen verwenden, die in den bereitgestellten Vertragsklauseln stehen.

2. ZITIERPFLICHT: JEDE Aussage MUSS mit einer Quellenangabe versehen werden.
   Format: [1], [2], etc. - verweist auf die Klausel-Nummern im Kontext.

3. NICHTWISSEN ZUGEBEN: Wenn die bereitgestellten Dokumente eine Frage NICHT beantworten können:
   → "Diese Information konnte ich in Ihren Verträgen nicht finden."
   → NIEMALS erfinden oder raten!

4. KEINE ALLGEMEINEN RECHTSAUSSAGEN: Sage NICHT "Laut {jurisdiction_name} Recht..." es sei denn, du zitierst eine spezifische Klausel.

5. UNSICHERHEIT KOMMUNIZIEREN: Bei Interpretationsspielraum:
   → "Diese Klausel könnte bedeuten... Ich empfehle jedoch die Rücksprache mit einem Anwalt."

═══════════════════════════════════════════════════════════════
                           ANTWORT-FORMAT
═══════════════════════════════════════════════════════════════

Antworte IMMER im folgenden JSON-Format:
{{
    "answer": "Deine Antwort mit [1], [2] Zitat-Markern",
    "citations": [
        {{
            "number": 1,
            "contract_id": "uuid-aus-dem-kontext",
            "contract_filename": "vertrag.pdf",
            "clause_text": "Exaktes Zitat aus dem Vertrag (max 200 Zeichen)",
            "page": 4,
            "paragraph": "§7 Abs. 2"
        }}
    ],
    "confidence": 0.85,
    "requires_lawyer": false,
    "follow_up_questions": ["Mögliche Folgefrage 1", "Mögliche Folgefrage 2"]
}}

CONFIDENCE SCALE:
- 0.9-1.0: Klare Antwort direkt aus Vertrag
- 0.7-0.9: Antwort aus Vertrag, leichte Interpretation nötig
- 0.5-0.7: Teilweise Antwort, einiges unklar
- 0.0-0.5: Kaum relevante Info gefunden

REQUIRES_LAWYER = true wenn:
- Rechtliche Interpretation komplex
- Haftungsrisiken bestehen
- Frage außerhalb deiner Wissensbasis
- Gerichtliche Schritte diskutiert werden"""

    def render_user(
        self,
        question: str,
        clauses: list[ClauseInput],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Render the user prompt with question and contract context.

        Args:
            question: User's legal question
            clauses: Relevant contract clauses (from KnowledgeRetriever)
            conversation_history: Previous Q&A pairs (optional)
        """
        # Build context section
        if clauses:
            context_parts = []
            for clause in clauses:
                page_info = f", Seite {clause.page}" if clause.page else ""
                context_parts.append(
                    f"[{clause.number}] {clause.contract_filename}{page_info}:\n"
                    f'"{clause.clause_text}"'
                )
            context_section = "\n\n".join(context_parts)
        else:
            context_section = "(Keine relevanten Vertragsklauseln gefunden)"

        # Build conversation history section
        history_section = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history[-4:]:  # Last 4 messages
                role = "Nutzer" if msg.get("role") == "user" else "Jurist"
                content = msg.get("content", "")[:500]  # Truncate long messages
                history_parts.append(f"{role}: {content}")
            history_section = "\n\n── BISHERIGES GESPRÄCH ──\n" + "\n\n".join(history_parts)

        return f"""══════════════════════════════════════════════════════════════
                    VERFÜGBARE VERTRAGSKLAUSELN
══════════════════════════════════════════════════════════════

{context_section}
{history_section}

══════════════════════════════════════════════════════════════
                         FRAGE DES NUTZERS
══════════════════════════════════════════════════════════════

{question}

══════════════════════════════════════════════════════════════

WICHTIG: Antworte NUR basierend auf den obigen Vertragsklauseln.
Wenn die Antwort nicht in den Klauseln steht, sage das ehrlich.
Antworte im JSON-Format."""

    def parse_response(self, response: str) -> LegalAdvisorResponse:
        """Parse AI response JSON into structured result.

        Includes fallback handling for malformed responses.
        """
        try:
            # Clean response (remove markdown code blocks if present)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Remove first line (```json) and last line (```)
                cleaned = "\n".join(lines[1:-1])

            data = json.loads(cleaned)

            # Parse citations
            citations = []
            for c in data.get("citations", []):
                citation = Citation(
                    number=c.get("number", 0),
                    contract_id=c.get("contract_id", ""),
                    contract_filename=c.get("contract_filename", ""),
                    clause_text=c.get("clause_text", ""),
                    page=c.get("page"),
                    paragraph=c.get("paragraph"),
                )
                citations.append(citation)

            return LegalAdvisorResponse(
                answer=data.get("answer", "Keine Antwort verfügbar."),
                citations=citations,
                confidence=float(data.get("confidence", 0.5)),
                requires_lawyer=bool(data.get("requires_lawyer", False)),
                follow_up_questions=data.get("follow_up_questions", []),
            )

        except json.JSONDecodeError as e:
            logger.error(
                "legal_advisor_response_parse_failed",
                error=str(e),
                response=response[:500],
            )

            # Return a safe fallback response
            return LegalAdvisorResponse(
                answer="Entschuldigung, ich konnte die Antwort nicht korrekt verarbeiten. "
                "Bitte versuchen Sie es erneut oder formulieren Sie Ihre Frage um.",
                citations=[],
                confidence=0.0,
                requires_lawyer=True,
                follow_up_questions=[],
            )

    def validate_citations(
        self,
        response: LegalAdvisorResponse,
        provided_clauses: list[ClauseInput],
    ) -> LegalAdvisorResponse:
        """Validate that all citations reference actual provided clauses.

        This is the CRITICAL anti-hallucination check.
        If AI cites something we didn't provide, we remove it.
        """
        # Build set of valid contract IDs
        valid_contract_ids = {clause.contract_id for clause in provided_clauses}

        # Build map of clause numbers to actual text
        clause_texts = {clause.number: clause.clause_text.lower() for clause in provided_clauses}

        validated_citations = []
        hallucinated_count = 0

        for citation in response.citations:
            # Check 1: Is the contract_id valid?
            if citation.contract_id not in valid_contract_ids:
                logger.warning(
                    "hallucinated_contract_id_detected",
                    cited_id=citation.contract_id,
                    valid_ids=list(valid_contract_ids),
                )
                hallucinated_count += 1
                continue

            # Check 2: Does the cited text roughly match what we provided?
            # Allow some flexibility since AI might paraphrase slightly
            if citation.number in clause_texts:
                original = clause_texts[citation.number]
                cited = citation.clause_text.lower()

                # Check if at least some words from citation appear in original
                cited_words = set(cited.split())
                original_words = set(original.split())
                overlap = len(cited_words & original_words)

                if overlap < 3:  # At least 3 words should match
                    logger.warning(
                        "hallucinated_clause_text_detected",
                        citation_number=citation.number,
                        cited_preview=cited[:100],
                        original_preview=original[:100],
                    )
                    hallucinated_count += 1
                    continue

            validated_citations.append(citation)

        # Penalize confidence if we found hallucinations
        if hallucinated_count > 0:
            response.confidence = max(0.0, response.confidence - (0.2 * hallucinated_count))
            logger.warning(
                "hallucinations_removed",
                count=hallucinated_count,
                new_confidence=response.confidence,
            )

        response.citations = validated_citations
        return response


# Fallback response when no contracts are found
NO_CONTRACTS_RESPONSE = LegalAdvisorResponse(
    answer="Ich konnte in Ihren hochgeladenen Verträgen keine relevanten Informationen zu dieser Frage finden. "
    "Bitte laden Sie relevante Verträge hoch oder formulieren Sie Ihre Frage anders.\n\n"
    "Falls Sie eine allgemeine Rechtsfrage haben, empfehle ich die Konsultation eines Rechtsanwalts.",
    citations=[],
    confidence=1.0,  # High confidence that we DON'T have the info
    requires_lawyer=True,
    follow_up_questions=[
        "Haben Sie einen passenden Vertrag hochgeladen?",
        "Können Sie Ihre Frage spezifischer formulieren?",
    ],
)
