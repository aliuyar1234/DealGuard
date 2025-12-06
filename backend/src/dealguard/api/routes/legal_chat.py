"""Legal Chat API routes - AI-Jurist feature."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dealguard.api.middleware.auth import CurrentUser, RequireMember
from dealguard.domain.legal.chat_service import LegalChatService
from dealguard.infrastructure.database.connection import SessionDep
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/legal", tags=["Legal Chat"])


# ─────────────────────────────────────────────────────────────
#                     SCHEMAS
# ─────────────────────────────────────────────────────────────


class CitationResponse(BaseModel):
    """Citation from a contract clause."""

    number: int
    contract_id: str
    contract_filename: str
    clause_text: str
    page: int | None = None
    paragraph: str | None = None


class MessageResponse(BaseModel):
    """A message in a conversation."""

    id: str
    role: str  # "user" or "assistant"
    content: str
    citations: list[CitationResponse] = []
    confidence: float | None = None
    requires_lawyer: bool = False
    created_at: str


class ConversationResponse(BaseModel):
    """A legal conversation."""

    id: str
    title: str | None
    created_at: str
    updated_at: str
    messages: list[MessageResponse] = []


class ConversationListResponse(BaseModel):
    """List of conversations."""

    items: list[ConversationResponse]
    total: int


class AskQuestionRequest(BaseModel):
    """Request to ask a legal question."""

    question: str = Field(..., min_length=3, max_length=2000)


class AskQuestionResponse(BaseModel):
    """Response from asking a legal question."""

    conversation_id: str
    message_id: str
    answer: str
    citations: list[CitationResponse]
    confidence: float
    requires_lawyer: bool
    follow_up_questions: list[str]
    # Cost tracking (optional)
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_cents: float | None = None


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    title: str | None = Field(None, max_length=255)


# ─────────────────────────────────────────────────────────────
#                   DEPENDENCIES
# ─────────────────────────────────────────────────────────────


async def get_chat_service(session: SessionDep) -> LegalChatService:
    """Get legal chat service."""
    return LegalChatService(session)


ChatServiceDep = Annotated[LegalChatService, Depends(get_chat_service)]


# ─────────────────────────────────────────────────────────────
#                      ROUTES
# ─────────────────────────────────────────────────────────────


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    user: RequireMember,
    service: ChatServiceDep,
    request: CreateConversationRequest | None = None,
) -> ConversationResponse:
    """Create a new legal conversation.

    Optional: Provide a title, otherwise auto-generated from first question.
    """
    title = request.title if request else None
    conversation = await service.create_conversation(title=title)

    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=[],
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: CurrentUser,
    service: ChatServiceDep,
    limit: int = 20,
    offset: int = 0,
) -> ConversationListResponse:
    """List all legal conversations for the current organization."""
    conversations = await service.list_conversations(limit=limit, offset=offset)

    items = [
        ConversationResponse(
            id=str(c.id),
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
            messages=[],  # Don't include messages in list view
        )
        for c in conversations
    ]

    # Get actual total count for proper pagination
    total = await service.count_conversations()

    return ConversationListResponse(
        items=items,
        total=total,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    user: CurrentUser,
    service: ChatServiceDep,
) -> ConversationResponse:
    """Get a conversation with all its messages."""
    conversation = await service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(404, "Gespräch nicht gefunden")

    messages = [
        MessageResponse(
            id=str(m.id),
            role=m.role.value,
            content=m.content,
            citations=[
                CitationResponse(**c) for c in m.message_metadata.get("citations", [])
            ],
            confidence=m.message_metadata.get("confidence"),
            requires_lawyer=m.message_metadata.get("requires_lawyer", False),
            created_at=m.created_at.isoformat(),
        )
        for m in conversation.messages
    ]

    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    user: RequireMember,
    service: ChatServiceDep,
) -> None:
    """Delete a conversation."""
    success = await service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(404, "Gespräch nicht gefunden")


@router.post("/conversations/{conversation_id}/ask", response_model=AskQuestionResponse)
async def ask_question_in_conversation(
    conversation_id: UUID,
    request: AskQuestionRequest,
    user: RequireMember,
    service: ChatServiceDep,
) -> AskQuestionResponse:
    """Ask a legal question in an existing conversation.

    The AI will:
    1. Search your contracts for relevant clauses
    2. Answer based ONLY on your contract content
    3. Cite sources for every claim
    4. Recommend a lawyer if the question is outside its scope

    Response includes confidence score (0-1) and citation details.
    """
    try:
        response = await service.ask_question(
            question=request.question,
            conversation_id=conversation_id,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    citations = [
        CitationResponse(
            number=c.get("number", 0),
            contract_id=c.get("contract_id", ""),
            contract_filename=c.get("contract_filename", ""),
            clause_text=c.get("clause_text", ""),
            page=c.get("page"),
            paragraph=c.get("paragraph"),
        )
        for c in response.citations
    ]

    return AskQuestionResponse(
        conversation_id=str(response.conversation_id),
        message_id=str(response.message_id),
        answer=response.answer,
        citations=citations,
        confidence=response.confidence,
        requires_lawyer=response.requires_lawyer,
        follow_up_questions=response.follow_up_questions,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_cents=response.cost_cents,
    )


@router.post("/ask", response_model=AskQuestionResponse)
async def ask_question(
    request: AskQuestionRequest,
    user: RequireMember,
    service: ChatServiceDep,
) -> AskQuestionResponse:
    """Ask a legal question (creates a new conversation).

    Convenience endpoint that:
    1. Creates a new conversation
    2. Asks the question
    3. Returns the response

    Use POST /conversations/{id}/ask for follow-up questions.
    """
    response = await service.ask_question(
        question=request.question,
        conversation_id=None,  # Creates new conversation
    )

    citations = [
        CitationResponse(
            number=c.get("number", 0),
            contract_id=c.get("contract_id", ""),
            contract_filename=c.get("contract_filename", ""),
            clause_text=c.get("clause_text", ""),
            page=c.get("page"),
            paragraph=c.get("paragraph"),
        )
        for c in response.citations
    ]

    return AskQuestionResponse(
        conversation_id=str(response.conversation_id),
        message_id=str(response.message_id),
        answer=response.answer,
        citations=citations,
        confidence=response.confidence,
        requires_lawyer=response.requires_lawyer,
        follow_up_questions=response.follow_up_questions,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_cents=response.cost_cents,
    )
