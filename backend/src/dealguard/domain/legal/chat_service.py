"""Legal chat service - orchestrates the AI-Jurist feature.

This is the main service that:
1. Searches for relevant contract clauses (RAG)
2. Builds prompts with anti-hallucination measures
3. Calls AI and validates responses
4. Stores conversations and messages
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dealguard.domain.legal.knowledge_retriever import (
    KnowledgeRetriever,
    ClauseContext,
)
from dealguard.domain.legal.company_profile import (
    CompanyProfile,
    CompanyProfileService,
)
from dealguard.infrastructure.ai.factory import get_ai_client
from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import (
    LegalAdvisorPromptV1,
    LegalAdvisorResponse,
    ClauseInput,
    NO_CONTRACTS_RESPONSE,
)
from dealguard.infrastructure.database.models.legal_chat import (
    LegalConversation,
    LegalMessage,
    MessageRole,
)
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChatResponse:
    """Response from the legal chat service."""

    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[dict]
    confidence: float
    requires_lawyer: bool
    follow_up_questions: list[str]
    # Cost tracking
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cents: float | None = None


class LegalChatService:
    """Service for legal Q&A conversations.

    Flow:
    1. User asks question
    2. Search contracts for relevant clauses (KnowledgeRetriever)
    3. Build prompt with clauses + conversation history
    4. Call AI with anti-hallucination prompt
    5. Validate citations
    6. Store message and return response
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id
        self.knowledge_retriever = KnowledgeRetriever(session, organization_id=organization_id)
        self.profile_service = CompanyProfileService(session, organization_id=organization_id)
        self.ai_client = get_ai_client()
        self.prompt = LegalAdvisorPromptV1()

    def _get_organization_id(self) -> UUID:
        return self.organization_id

    def _get_user_id(self) -> UUID:
        return self.user_id

    # ─────────────────────────────────────────────────────────────
    #                    CONVERSATION CRUD
    # ─────────────────────────────────────────────────────────────

    async def create_conversation(
        self,
        title: str | None = None,
    ) -> LegalConversation:
        """Create a new legal conversation."""
        conversation = LegalConversation(
            id=uuid4(),
            organization_id=self._get_organization_id(),
            created_by=self._get_user_id(),
            title=title,
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)

        logger.info(
            "conversation_created",
            conversation_id=str(conversation.id),
            organization_id=str(self._get_organization_id()),
        )

        return conversation

    async def get_conversation(
        self,
        conversation_id: UUID,
    ) -> LegalConversation | None:
        """Get a conversation by ID."""
        query = (
            select(LegalConversation)
            .where(LegalConversation.id == conversation_id)
            .where(LegalConversation.organization_id == self._get_organization_id())
            .where(LegalConversation.deleted_at.is_(None))
            .options(selectinload(LegalConversation.messages))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[LegalConversation]:
        """List conversations for the current organization."""
        query = (
            select(LegalConversation)
            .where(LegalConversation.organization_id == self._get_organization_id())
            .where(LegalConversation.deleted_at.is_(None))
            .order_by(LegalConversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_conversations(self) -> int:
        """Count total conversations for the current organization."""
        from sqlalchemy import func
        query = (
            select(func.count(LegalConversation.id))
            .where(LegalConversation.organization_id == self._get_organization_id())
            .where(LegalConversation.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_conversation(
        self,
        conversation_id: UUID,
    ) -> bool:
        """Soft-delete a conversation."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info(
            "conversation_deleted",
            conversation_id=str(conversation_id),
        )

        return True

    # ─────────────────────────────────────────────────────────────
    #                       ASK QUESTION
    # ─────────────────────────────────────────────────────────────

    async def ask_question(
        self,
        question: str,
        conversation_id: UUID | None = None,
    ) -> ChatResponse:
        """Ask a legal question about the company's contracts.

        This is the main entry point for legal Q&A.

        Args:
            question: The user's legal question
            conversation_id: Existing conversation ID (optional)

        Returns:
            ChatResponse with answer, citations, and metadata
        """
        org_id = self._get_organization_id()
        user_id = self._get_user_id()

        # Get or create conversation
        if conversation_id:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation not found: {conversation_id}")
        else:
            conversation = await self.create_conversation()

        # Save user message
        user_message = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=question,
        )

        # Update conversation title if first message
        if not conversation.title:
            conversation.title = self._generate_title(question)
            await self.session.flush()

        # ─────────────────────────────────────────────────────────
        #                  RAG: RETRIEVE CONTEXT
        # ─────────────────────────────────────────────────────────

        clauses, search_query = await self.knowledge_retriever.build_context_for_question(
            question
        )

        # If no contracts found, return early with helpful message
        if not clauses:
            logger.info(
                "no_contracts_found_for_question",
                question=question[:100],
                organization_id=str(org_id),
            )

            assistant_message = await self._save_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=NO_CONTRACTS_RESPONSE.answer,
                metadata={
                    "citations": [],
                    "confidence": NO_CONTRACTS_RESPONSE.confidence,
                    "requires_lawyer": NO_CONTRACTS_RESPONSE.requires_lawyer,
                    "follow_up_questions": NO_CONTRACTS_RESPONSE.follow_up_questions,
                    "search_query": search_query,
                    "contracts_found": 0,
                },
            )

            return ChatResponse(
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                answer=NO_CONTRACTS_RESPONSE.answer,
                citations=[],
                confidence=NO_CONTRACTS_RESPONSE.confidence,
                requires_lawyer=NO_CONTRACTS_RESPONSE.requires_lawyer,
                follow_up_questions=NO_CONTRACTS_RESPONSE.follow_up_questions,
            )

        # ─────────────────────────────────────────────────────────
        #                  BUILD PROMPT
        # ─────────────────────────────────────────────────────────

        # Get company profile
        profile = await self.profile_service.get_profile()

        # Convert clauses to prompt input format
        clause_inputs = [
            ClauseInput(
                number=i + 1,
                contract_id=str(c.contract_id),
                contract_filename=c.contract_filename,
                clause_text=c.clause_text,
                page=c.page,
            )
            for i, c in enumerate(clauses)
        ]

        # Get conversation history
        history = await self._get_conversation_history(conversation.id)

        # Render prompts
        system_prompt = self.prompt.render_system(
            company_name=profile.company_name,
            jurisdiction=profile.jurisdiction,
        )
        user_prompt = self.prompt.render_user(
            question=question,
            clauses=clause_inputs,
            conversation_history=history,
        )

        # ─────────────────────────────────────────────────────────
        #                    CALL AI
        # ─────────────────────────────────────────────────────────

        logger.info(
            "calling_ai_for_legal_question",
            question=question[:100],
            clauses_count=len(clauses),
            conversation_id=str(conversation.id),
        )

        ai_response = await self.ai_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,  # Low for factual accuracy
            action="legal_chat",
            resource_id=conversation.id,
        )

        # ─────────────────────────────────────────────────────────
        #              PARSE AND VALIDATE RESPONSE
        # ─────────────────────────────────────────────────────────

        parsed = self.prompt.parse_response(ai_response.content)

        # CRITICAL: Validate citations against provided clauses
        validated = self.prompt.validate_citations(parsed, clause_inputs)

        # ─────────────────────────────────────────────────────────
        #                  SAVE RESPONSE
        # ─────────────────────────────────────────────────────────

        assistant_message = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=validated.answer,
            metadata={
                "citations": [
                    {
                        "number": c.number,
                        "contract_id": c.contract_id,
                        "contract_filename": c.contract_filename,
                        "clause_text": c.clause_text,
                        "page": c.page,
                        "paragraph": c.paragraph,
                    }
                    for c in validated.citations
                ],
                "confidence": validated.confidence,
                "requires_lawyer": validated.requires_lawyer,
                "follow_up_questions": validated.follow_up_questions,
                "search_query": search_query,
                "contracts_searched": [str(c.contract_id) for c in clauses],
            },
            input_tokens=ai_response.input_tokens,
            output_tokens=ai_response.output_tokens,
            cost_cents=ai_response.cost_cents,
        )

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info(
            "legal_question_answered",
            conversation_id=str(conversation.id),
            message_id=str(assistant_message.id),
            confidence=validated.confidence,
            citations_count=len(validated.citations),
            requires_lawyer=validated.requires_lawyer,
            cost_cents=ai_response.cost_cents,
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=validated.answer,
            citations=[c.__dict__ for c in validated.citations],
            confidence=validated.confidence,
            requires_lawyer=validated.requires_lawyer,
            follow_up_questions=validated.follow_up_questions,
            input_tokens=ai_response.input_tokens,
            output_tokens=ai_response.output_tokens,
            cost_cents=ai_response.cost_cents,
        )

    # ─────────────────────────────────────────────────────────────
    #                      HELPERS
    # ─────────────────────────────────────────────────────────────

    async def _save_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        metadata: dict | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_cents: float | None = None,
    ) -> LegalMessage:
        """Save a message to the database."""
        message = LegalMessage(
            id=uuid4(),
            organization_id=self._get_organization_id(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=metadata or {},
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=cost_cents,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def _get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 6,
    ) -> list[dict]:
        """Get recent conversation history for context."""
        query = (
            select(LegalMessage)
            .where(LegalMessage.conversation_id == conversation_id)
            .order_by(LegalMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

    def _generate_title(self, question: str) -> str:
        """Generate a title from the first question."""
        # Take first 50 chars, cut at word boundary
        if len(question) <= 50:
            return question

        title = question[:50]
        last_space = title.rfind(" ")
        if last_space > 20:
            title = title[:last_space]

        return title + "..."
