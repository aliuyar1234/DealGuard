"""Add legal chat tables for AI-Jurist feature.

Revision ID: 003_add_legal_chat
Revises: 002_add_partners
Create Date: 2024-12-05
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "003_add_legal_chat"
down_revision: str | None = "002_add_partners"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create legal_conversations table
    op.create_table(
        "legal_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        # Conversation info
        sa.Column("title", sa.String(255), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_legal_conversations_organization_id", "legal_conversations", ["organization_id"])
    op.create_index("ix_legal_conversations_created_by", "legal_conversations", ["created_by"])

    # Create legal_messages table
    op.create_table(
        "legal_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        # Message content
        sa.Column("role", sa.String(20), nullable=False),  # 'user' or 'assistant'
        sa.Column("content", sa.Text(), nullable=False),
        # Metadata for AI responses (citations, confidence, search query used, etc.)
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        # Cost tracking (for assistant messages)
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_cents", sa.Float(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["legal_conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_legal_messages_organization_id", "legal_messages", ["organization_id"])
    op.create_index("ix_legal_messages_conversation_id", "legal_messages", ["conversation_id"])

    # Add Full-Text Search index on contracts.raw_text for German language
    # This enables fast searching through contract content
    op.execute("""
        CREATE INDEX ix_contracts_raw_text_fts
        ON contracts
        USING GIN (to_tsvector('german', COALESCE(raw_text, '')))
    """)


def downgrade() -> None:
    # Drop FTS index
    op.execute("DROP INDEX IF EXISTS ix_contracts_raw_text_fts")

    # Drop tables
    op.drop_table("legal_messages")
    op.drop_table("legal_conversations")
