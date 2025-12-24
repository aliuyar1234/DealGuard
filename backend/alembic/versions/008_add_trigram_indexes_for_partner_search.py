"""Add trigram indexes for fast ILIKE partner search.

Partner search uses `ILIKE '%query%'` across several text columns. A btree index
cannot support leading-wildcard searches, which causes full scans within a
tenant for large datasets.

We use `pg_trgm` GIN trigram indexes to accelerate substring searches.

Revision ID: 008_add_trigram_indexes_for_partner_search
Revises: 007_add_hot_path_indexes
Create Date: 2025-12-24
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic
revision: str = "008_add_trigram_indexes_for_partner_search"
down_revision: str | None = "007_add_hot_path_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOTE: pg_trgm extension is enabled in 001_initial; keep this migration
    # focused on indexes only.
    op.create_index(
        "ix_partners_name_trgm",
        "partners",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_partners_handelsregister_id_trgm",
        "partners",
        ["handelsregister_id"],
        postgresql_using="gin",
        postgresql_ops={"handelsregister_id": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_partners_vat_id_trgm",
        "partners",
        ["vat_id"],
        postgresql_using="gin",
        postgresql_ops={"vat_id": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_partners_city_trgm",
        "partners",
        ["city"],
        postgresql_using="gin",
        postgresql_ops={"city": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_partners_city_trgm", table_name="partners")
    op.drop_index("ix_partners_vat_id_trgm", table_name="partners")
    op.drop_index("ix_partners_handelsregister_id_trgm", table_name="partners")
    op.drop_index("ix_partners_name_trgm", table_name="partners")
