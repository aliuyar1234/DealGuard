"""Add proactive AI-Jurist system tables.

This migration adds:
- contract_deadlines: Extracted dates/deadlines from contracts
- proactive_alerts: AI-generated alerts with recommended actions
- alert_actions: Possible actions for each alert type
- compliance_checks: Periodic compliance scan results

Revision ID: 004_add_proactive_system
Revises: 003_add_legal_chat
Create Date: 2024-12-05
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "004_add_proactive_system"
down_revision: str | None = "003_add_legal_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────
    # CONTRACT DEADLINES - Extracted dates from contracts
    # ─────────────────────────────────────────────────────────────
    op.create_table(
        "contract_deadlines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        # Deadline info
        sa.Column("deadline_type", sa.String(50), nullable=False),
        # Types: termination_notice, auto_renewal, payment_due, warranty_end,
        #        contract_end, review_date, price_adjustment, other
        sa.Column("deadline_date", sa.Date(), nullable=False),
        sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="30"),
        # Extracted clause
        sa.Column("source_clause", sa.Text(), nullable=True),
        sa.Column("clause_location", postgresql.JSONB(), nullable=True),
        # AI extraction metadata
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("extracted_by_model", sa.String(100), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        # Status
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        # Status: active, handled, expired, dismissed
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handled_by", sa.UUID(), nullable=True),
        sa.Column("handled_action", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handled_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_contract_deadlines_organization_id", "contract_deadlines", ["organization_id"])
    op.create_index("ix_contract_deadlines_contract_id", "contract_deadlines", ["contract_id"])
    op.create_index("ix_contract_deadlines_deadline_date", "contract_deadlines", ["deadline_date"])
    op.create_index("ix_contract_deadlines_status", "contract_deadlines", ["status"])

    # ─────────────────────────────────────────────────────────────
    # PROACTIVE ALERTS - AI-generated alerts
    # ─────────────────────────────────────────────────────────────
    op.create_table(
        "proactive_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        # Source (what triggered this alert)
        sa.Column("source_type", sa.String(50), nullable=False),
        # Source types: deadline, partner_risk, compliance, opportunity, contract_risk
        sa.Column("source_id", sa.UUID(), nullable=True),  # FK to deadline/partner/contract
        # Alert content
        sa.Column("alert_type", sa.String(50), nullable=False),
        # Types: deadline_approaching, auto_renewal_warning, partner_risk_change,
        #        compliance_issue, contract_risk, opportunity, payment_due
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        # Severity: info, low, medium, high, critical
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # AI-generated recommendation
        sa.Column("ai_recommendation", sa.Text(), nullable=True),
        sa.Column("recommended_actions", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Structure: [{"action": "terminate", "label": "Kündigen", "params": {...}}, ...]
        # Related entities
        sa.Column("related_contract_id", sa.UUID(), nullable=True),
        sa.Column("related_partner_id", sa.UUID(), nullable=True),
        # Status
        sa.Column("status", sa.String(50), nullable=False, server_default="new"),
        # Status: new, seen, in_progress, resolved, dismissed, snoozed
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolution_action", sa.String(100), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),  # When action is needed by
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_contract_id"], ["contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_partner_id"], ["partners.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_proactive_alerts_organization_id", "proactive_alerts", ["organization_id"])
    op.create_index("ix_proactive_alerts_status", "proactive_alerts", ["status"])
    op.create_index("ix_proactive_alerts_severity", "proactive_alerts", ["severity"])
    op.create_index("ix_proactive_alerts_created_at", "proactive_alerts", ["created_at"])
    op.create_index("ix_proactive_alerts_due_date", "proactive_alerts", ["due_date"])

    # ─────────────────────────────────────────────────────────────
    # COMPLIANCE CHECKS - Periodic compliance scan results
    # ─────────────────────────────────────────────────────────────
    op.create_table(
        "compliance_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        # Check info
        sa.Column("check_type", sa.String(50), nullable=False),
        # Types: gdpr, avv, liability_cap, payment_terms, termination_clause,
        #        jurisdiction, ip_rights, confidentiality, warranty
        sa.Column("status", sa.String(50), nullable=False),
        # Status: compliant, warning, non_compliant, needs_review
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        # Finding details
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_clause", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("suggested_change", sa.Text(), nullable=True),
        # Metadata
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ai_model_version", sa.String(100), nullable=True),
        # Resolution
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_compliance_checks_organization_id", "compliance_checks", ["organization_id"])
    op.create_index("ix_compliance_checks_contract_id", "compliance_checks", ["contract_id"])
    op.create_index("ix_compliance_checks_status", "compliance_checks", ["status"])

    # ─────────────────────────────────────────────────────────────
    # RISK SNAPSHOTS - Daily risk score snapshots for trending
    # ─────────────────────────────────────────────────────────────
    op.create_table(
        "risk_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        # Aggregate scores
        sa.Column("overall_risk_score", sa.Integer(), nullable=False),
        sa.Column("contract_risk_score", sa.Integer(), nullable=False),
        sa.Column("partner_risk_score", sa.Integer(), nullable=False),
        sa.Column("compliance_score", sa.Integer(), nullable=False),
        # Counts
        sa.Column("total_contracts", sa.Integer(), nullable=False),
        sa.Column("high_risk_contracts", sa.Integer(), nullable=False),
        sa.Column("total_partners", sa.Integer(), nullable=False),
        sa.Column("high_risk_partners", sa.Integer(), nullable=False),
        sa.Column("pending_deadlines", sa.Integer(), nullable=False),
        sa.Column("open_alerts", sa.Integer(), nullable=False),
        # Detailed breakdown (JSONB for flexibility)
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "snapshot_date", name="uq_risk_snapshot_org_date"),
    )
    op.create_index("ix_risk_snapshots_organization_id", "risk_snapshots", ["organization_id"])
    op.create_index("ix_risk_snapshots_snapshot_date", "risk_snapshots", ["snapshot_date"])


def downgrade() -> None:
    op.drop_table("risk_snapshots")
    op.drop_table("compliance_checks")
    op.drop_table("proactive_alerts")
    op.drop_table("contract_deadlines")
