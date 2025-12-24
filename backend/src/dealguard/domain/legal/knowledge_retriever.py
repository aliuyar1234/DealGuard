"""Knowledge retriever for searching contracts.

Contracts are stored encrypted at rest. To enable scalable keyword search without
decrypting all contracts, we use a separate token index table based on HMAC-hashed
tokens.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.infrastructure.database.models.contract import Contract
from dealguard.infrastructure.database.models.contract_search import ContractSearchToken
from dealguard.shared.logging import get_logger
from dealguard.shared.search_tokens import token_hashes_from_query

logger = get_logger(__name__)


@dataclass
class ClauseContext:
    """A relevant clause extracted from a contract.

    Used as context for the AI when answering legal questions.
    """

    contract_id: UUID
    contract_filename: str
    clause_text: str  # ~500 chars of relevant text
    relevance_score: float  # PostgreSQL ts_rank score
    # Location info (if available)
    page: int | None = None
    paragraph: str | None = None


@dataclass
class ContractSearchResult:
    """A contract that matches the search query."""

    contract_id: UUID
    filename: str
    contract_type: str | None
    raw_text: str
    relevance_score: float


class KnowledgeRetriever:
    """Retrieves relevant contract content for legal questions.

    The retriever:
    1. Searches contracts using a hashed token index
    2. Extracts relevant clause windows (~500 chars)
    3. Returns context for the AI prompt
    """

    # Maximum characters to extract around a match
    CLAUSE_WINDOW_SIZE = 500
    # Maximum number of contracts to search
    MAX_CONTRACTS = 5
    # Maximum total context length (to avoid huge prompts)
    MAX_TOTAL_CONTEXT = 3000

    def __init__(self, session: AsyncSession, *, organization_id: UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def _get_organization_id(self) -> UUID:
        """Get current tenant's organization ID."""
        return self.organization_id

    async def search_contracts(
        self,
        query: str,
        *,
        limit: int = 5,
    ) -> list[ContractSearchResult]:
        """Search contracts using the hashed token index."""
        org_id = self._get_organization_id()

        token_hashes = token_hashes_from_query(query)
        if not token_hashes:
            return []

        matches = (
            select(
                ContractSearchToken.contract_id.label("contract_id"),
                func.count().label("match_count"),
            )
            .where(ContractSearchToken.organization_id == org_id)
            .where(ContractSearchToken.token_hash.in_(token_hashes))
            .group_by(ContractSearchToken.contract_id)
            .subquery()
        )

        query_stmt = (
            select(Contract, matches.c.match_count)
            .join(matches, Contract.id == matches.c.contract_id)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
            .where(Contract._raw_text_encrypted.is_not(None))
            .order_by(matches.c.match_count.desc(), Contract.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query_stmt)
        rows = result.all()

        logger.info(
            "contract_search_completed",
            query=query,
            results_count=len(rows),
            organization_id=str(org_id),
        )

        results: list[ContractSearchResult] = []
        for contract, match_count in rows:
            contract_text = contract.contract_text
            if not contract_text:
                continue

            relevance = float(match_count) / float(len(token_hashes))
            results.append(
                ContractSearchResult(
                    contract_id=contract.id,
                    filename=contract.filename,
                    contract_type=contract.contract_type.value
                    if hasattr(contract.contract_type, "value")
                    else contract.contract_type,
                    raw_text=contract_text,
                    relevance_score=relevance,
                )
            )

        return results

    async def get_all_contracts(
        self,
        *,
        limit: int = 10,
    ) -> list[ContractSearchResult]:
        """Get all contracts for the organization (for general questions).

        Used when the query doesn't match specific text but we still
        want to provide contract context.

        Args:
            limit: Maximum number of contracts to return

        Returns:
            List of contracts sorted by creation date (newest first)
        """
        org_id = self._get_organization_id()

        query_stmt = (
            select(Contract)
            .where(Contract.organization_id == org_id)
            .where(Contract.deleted_at.is_(None))
            .where(Contract._raw_text_encrypted.is_not(None))
            .where(Contract.status == "completed")
            .order_by(Contract.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query_stmt)
        contracts = result.scalars().all()

        results: list[ContractSearchResult] = []
        for contract in contracts:
            contract_text = contract.contract_text
            if not contract_text:
                continue
            results.append(
                ContractSearchResult(
                    contract_id=contract.id,
                    filename=contract.filename,
                    contract_type=contract.contract_type.value
                    if contract.contract_type is not None
                    else None,
                    raw_text=contract_text,
                    relevance_score=0.5,
                )
            )

        return results

    def extract_relevant_clauses(
        self,
        search_results: list[ContractSearchResult],
        query: str,
    ) -> list[ClauseContext]:
        """Extract relevant clause windows from search results.

        Instead of sending the entire contract text to the AI,
        we extract ~500 character windows around relevant terms.

        Args:
            search_results: Contracts that matched the search
            query: Original search query (to find clause positions)

        Returns:
            List of clause contexts for AI prompt
        """
        clauses: list[ClauseContext] = []
        total_chars = 0

        # Split query into terms for matching
        query_terms = self._normalize_query_terms(query)

        for result in search_results:
            if total_chars >= self.MAX_TOTAL_CONTEXT:
                break

            # Find positions of query terms in text
            positions = self._find_term_positions(
                result.raw_text.lower(),
                query_terms,
            )

            if positions:
                # Extract window around first match
                pos = positions[0]
                clause_text = self._extract_window(
                    result.raw_text,
                    pos,
                    self.CLAUSE_WINDOW_SIZE,
                )
            else:
                # No exact match found, take the beginning of contract
                # (might be useful for general questions)
                clause_text = result.raw_text[: self.CLAUSE_WINDOW_SIZE]

            # Estimate page number (rough: ~3000 chars per page)
            page_estimate = (pos // 3000) + 1 if positions else 1

            clause = ClauseContext(
                contract_id=result.contract_id,
                contract_filename=result.filename,
                clause_text=clause_text.strip(),
                relevance_score=result.relevance_score,
                page=page_estimate,
            )
            clauses.append(clause)
            total_chars += len(clause_text)

        logger.debug(
            "clauses_extracted",
            clause_count=len(clauses),
            total_chars=total_chars,
            query=query,
        )

        return clauses

    def _normalize_query_terms(self, query: str) -> list[str]:
        """Normalize query into searchable terms.

        Removes common German stop words and normalizes case.
        """
        # Common German stop words to ignore
        stop_words = {
            "der",
            "die",
            "das",
            "den",
            "dem",
            "des",
            "ein",
            "eine",
            "einer",
            "einem",
            "einen",
            "und",
            "oder",
            "aber",
            "wenn",
            "weil",
            "ist",
            "sind",
            "war",
            "waren",
            "wird",
            "werden",
            "hat",
            "haben",
            "hatte",
            "hatten",
            "ich",
            "du",
            "er",
            "sie",
            "es",
            "wir",
            "ihr",
            "mein",
            "meine",
            "dein",
            "deine",
            "sein",
            "seine",
            "was",
            "wer",
            "wie",
            "wo",
            "wann",
            "warum",
            "zu",
            "von",
            "mit",
            "bei",
            "für",
            "auf",
            "an",
            "in",
            "nicht",
            "kein",
            "keine",
            "auch",
            "noch",
            "nur",
            "schon",
        }

        words = query.lower().split()
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _find_term_positions(
        self,
        text: str,
        terms: list[str],
    ) -> list[int]:
        """Find positions of query terms in text."""
        positions = []
        for term in terms:
            pos = text.find(term)
            if pos != -1:
                positions.append(pos)
        return sorted(positions)

    def _extract_window(
        self,
        text: str,
        position: int,
        window_size: int,
    ) -> str:
        """Extract a text window centered around a position.

        Tries to start/end at sentence boundaries for readability.
        """
        half_window = window_size // 2

        # Calculate start and end positions
        start = max(0, position - half_window)
        end = min(len(text), position + half_window)

        # Try to expand to sentence boundaries
        # Look backwards for sentence start (. ! ? followed by space)
        for i in range(start, max(0, start - 100), -1):
            if i > 0 and text[i - 1] in ".!?" and text[i] in " \n":
                start = i + 1
                break

        # Look forwards for sentence end
        for i in range(end, min(len(text), end + 100)):
            if text[i] in ".!?" and (i + 1 >= len(text) or text[i + 1] in " \n"):
                end = i + 1
                break

        extracted = text[start:end].strip()

        # Add ellipsis if truncated
        if start > 0:
            extracted = "..." + extracted
        if end < len(text):
            extracted = extracted + "..."

        return extracted

    async def build_context_for_question(
        self,
        question: str,
    ) -> tuple[list[ClauseContext], str]:
        """Build full context for a legal question.

        This is the main entry point for the chat service.

        Args:
            question: User's legal question

        Returns:
            Tuple of (clause contexts, search query used)
        """
        # First try specific search
        search_results = await self.search_contracts(
            question,
            limit=self.MAX_CONTRACTS,
        )

        # If no results, try getting all contracts
        if not search_results:
            logger.info(
                "no_search_results_fallback_to_all",
                question=question,
            )
            search_results = await self.get_all_contracts(
                limit=self.MAX_CONTRACTS,
            )

        # Extract relevant clauses
        clauses = self.extract_relevant_clauses(search_results, question)

        return clauses, question
