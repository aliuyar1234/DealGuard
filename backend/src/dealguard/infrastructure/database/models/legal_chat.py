"""Legal chat models for AI-Jurist feature."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealguard.infrastructure.database.models.base import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from dealguard.infrastructure.database.models.organization import Organization
    from dealguard.infrastructure.database.models.user import User


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "user"
    ASSISTANT = "assistant"


class LegalConversation(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """A legal Q&A conversation thread.

    Users can ask legal questions about their contracts.
    Each conversation contains multiple messages (questions & answers).
    """

    __tablename__ = "legal_conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Who created this conversation
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Auto-generated from first question
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        backref="legal_conversations",
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User",
        backref="legal_conversations",
        foreign_keys=[created_by],
    )
    messages: Mapped[list["LegalMessage"]] = relationship(
        "LegalMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="LegalMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<LegalConversation {self.title or 'Untitled'}>"


class LegalMessage(Base, TenantMixin):
    """A single message in a legal conversation.

    Can be from 'user' (question) or 'assistant' (AI response).
    Assistant messages include metadata: citations, confidence, search query.
    """

    __tablename__ = "legal_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Belongs to conversation
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("legal_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Message metadata for AI responses
    # Structure:
    # {
    #     "citations": [
    #         {
    #             "number": 1,
    #             "contract_id": "uuid",
    #             "contract_filename": "vertrag.pdf",
    #             "clause_text": "Exaktes Zitat...",
    #             "location": {"page": 4, "paragraph": "§7"}
    #         }
    #     ],
    #     "confidence": 0.85,
    #     "requires_lawyer": false,
    #     "search_query": "kündigungsfrist",
    #     "contracts_searched": ["uuid1", "uuid2"]
    # }
    message_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Cost tracking (only for assistant messages)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_cents: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    conversation: Mapped["LegalConversation"] = relationship(
        "LegalConversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<LegalMessage {self.role}: {preview}>"

    @property
    def citations(self) -> list[dict]:
        """Get citations from message_metadata."""
        return self.message_metadata.get("citations", [])

    @property
    def confidence(self) -> float | None:
        """Get confidence score from message_metadata."""
        return self.message_metadata.get("confidence")

    @property
    def requires_lawyer(self) -> bool:
        """Check if AI recommends consulting a lawyer."""
        return self.message_metadata.get("requires_lawyer", False)
