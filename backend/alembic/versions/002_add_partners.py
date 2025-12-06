"""Add partner intelligence tables.

Revision ID: 002_add_partners
Revises: 001_initial
Create Date: 2024-12-04
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "002_add_partners"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create partners table
    op.create_table(
        "partners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        # Basic info
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("partner_type", sa.String(50), nullable=False, server_default="other"),
        # Identifiers
        sa.Column("handelsregister_id", sa.String(50), nullable=True),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("vat_id", sa.String(50), nullable=True),
        # Address
        sa.Column("street", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(2), nullable=False, server_default="DE"),
        # Contact
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        # Risk assessment
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        # External data cache
        sa.Column("external_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        # Watchlist
        sa.Column("is_watched", sa.Boolean(), nullable=False, server_default="false"),
        # Notes
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_partners_organization_id", "partners", ["organization_id"])
    op.create_index("ix_partners_name", "partners", ["name"])

    # Create partner_checks table
    op.create_table(
        "partner_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("partner_id", sa.UUID(), nullable=False),
        # Check details
        sa.Column("check_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        # Results
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        # Provider info
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        # Error handling
        sa.Column("error_message", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_partner_checks_organization_id", "partner_checks", ["organization_id"])
    op.create_index("ix_partner_checks_partner_id", "partner_checks", ["partner_id"])

    # Create partner_alerts table
    op.create_table(
        "partner_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("partner_id", sa.UUID(), nullable=False),
        # Alert details
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # Source
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        # Status
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_by", sa.UUID(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dismissed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_partner_alerts_organization_id", "partner_alerts", ["organization_id"])
    op.create_index("ix_partner_alerts_partner_id", "partner_alerts", ["partner_id"])

    # Create contract_partners junction table
    op.create_table(
        "contract_partners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        sa.Column("partner_id", sa.UUID(), nullable=False),
        # Details
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("contract_id", "partner_id", name="uq_contract_partner"),
    )
    op.create_index("ix_contract_partners_organization_id", "contract_partners", ["organization_id"])
    op.create_index("ix_contract_partners_contract_id", "contract_partners", ["contract_id"])
    op.create_index("ix_contract_partners_partner_id", "contract_partners", ["partner_id"])


def downgrade() -> None:
    op.drop_table("contract_partners")
    op.drop_table("partner_alerts")
    op.drop_table("partner_checks")
    op.drop_table("partners")
