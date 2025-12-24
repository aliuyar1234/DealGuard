"""Add contract search token index for encrypted contract text.

Revision ID: 005_add_contract_search_tokens
Revises: 004_add_proactive_system
Create Date: 2025-12-24
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = "005_add_contract_search_tokens"
down_revision: str | None = "004_add_proactive_system"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract_search_tokens",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("organization_id", "token_hash", "contract_id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
    )

    # Supports "replace index for one contract" operations (delete by org+contract).
    op.create_index(
        "ix_contract_search_tokens_org_contract",
        "contract_search_tokens",
        ["organization_id", "contract_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_contract_search_tokens_org_contract", table_name="contract_search_tokens")
    op.drop_table("contract_search_tokens")

