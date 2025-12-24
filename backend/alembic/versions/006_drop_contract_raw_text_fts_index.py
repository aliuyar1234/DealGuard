"""Drop contracts.raw_text full-text-search index.

The old FTS index was created for plaintext contract text. Contract text is now
stored encrypted, which makes the index:
- Incorrect (searching ciphertext is meaningless)
- Expensive (GIN maintenance on large encrypted blobs)
- Storage-heavy (random ciphertext creates many unique lexemes)

We replaced contract search with a hashed token index (see revision
005_add_contract_search_tokens), so this index should be removed.

Revision ID: 006_drop_contract_raw_text_fts_index
Revises: 005_add_contract_search_tokens
Create Date: 2025-12-24
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic
revision: str = "006_drop_contract_raw_text_fts_index"
down_revision: str | None = "005_add_contract_search_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_contracts_raw_text_fts")


def downgrade() -> None:
    # Recreate the original index for legacy plaintext deployments.
    op.execute(
        """
        CREATE INDEX ix_contracts_raw_text_fts
        ON contracts
        USING GIN (to_tsvector('german', COALESCE(raw_text, '')))
        """
    )
