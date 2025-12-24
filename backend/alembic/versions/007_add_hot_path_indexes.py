"""Add indexes for hot-path queries.

These indexes target frequent filter/sort patterns used by:
- Risk radar aggregation queries (contracts/partners risk)
- Partner list endpoints (order by name, watched/high-risk filters)
- Deadline monitoring queries (status + date windows)

Revision ID: 007_add_hot_path_indexes
Revises: 006_drop_contract_raw_text_fts_index
Create Date: 2025-12-24
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic
revision: str = "007_add_hot_path_indexes"
down_revision: str | None = "006_drop_contract_raw_text_fts_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Contracts risk radar: WHERE organization_id = ? AND risk_score >= ?
    op.create_index(
        "ix_contract_analyses_org_risk_score",
        "contract_analyses",
        ["organization_id", "risk_score"],
    )

    # Partners: order-by name within tenant
    op.create_index(
        "ix_partners_org_name",
        "partners",
        ["organization_id", "name"],
    )

    # Partners: watchlist filter + name sorting
    op.create_index(
        "ix_partners_org_is_watched_name",
        "partners",
        ["organization_id", "is_watched", "name"],
    )

    # Partners: high-risk filter + risk_score sorting (btree can scan backwards)
    op.create_index(
        "ix_partners_org_risk_level_risk_score",
        "partners",
        ["organization_id", "risk_level", "risk_score"],
    )

    # Deadlines: status + upcoming/overdue date windows per tenant
    op.create_index(
        "ix_contract_deadlines_org_status_deadline_date",
        "contract_deadlines",
        ["organization_id", "status", "deadline_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_deadlines_org_status_deadline_date",
        table_name="contract_deadlines",
    )
    op.drop_index(
        "ix_partners_org_risk_level_risk_score",
        table_name="partners",
    )
    op.drop_index(
        "ix_partners_org_is_watched_name",
        table_name="partners",
    )
    op.drop_index(
        "ix_partners_org_name",
        table_name="partners",
    )
    op.drop_index(
        "ix_contract_analyses_org_risk_score",
        table_name="contract_analyses",
    )
