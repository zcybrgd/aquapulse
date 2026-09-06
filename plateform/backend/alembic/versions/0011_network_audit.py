"""Unified agent audit events. No network decision-engine table.

Downgrade removes only these Step 12 additions.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_network_audit"
down_revision = "0010_maintenance_center"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_agent_runs_agent_run_type_allowed", "agent_runs", type_="check")
    op.create_check_constraint(
        "ck_agent_runs_agent_run_type_allowed",
        "agent_runs",
        "agent_type IN ('investigation_agent', 'response_agent', 'network_management_agent')",
    )

    op.add_column(
        "agent_findings",
        sa.Column("anomaly_detection_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_agent_findings_anomaly_detection",
        "agent_findings",
        "anomaly_detections",
        ["anomaly_detection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_agent_findings_anomaly_detection_id", "agent_findings", ["anomaly_detection_id"])

    op.create_table(
        "agent_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("agent_code", sa.String(length=80), nullable=False),
        sa.Column("contract_version", sa.String(length=20), nullable=False),
        sa.Column("pipeline_stage", sa.String(length=40), nullable=False),
        sa.Column("node_name", sa.String(length=120), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("incident_public_id", sa.String(length=32), nullable=True),
        sa.Column("detection_public_id", sa.String(length=32), nullable=True),
        sa.Column("asset_public_id", sa.String(length=80), nullable=True),
        sa.Column("external_cluster_id", sa.String(length=120), nullable=True),
        sa.Column("external_device_id", sa.String(length=120), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("input_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reasoning_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("safety_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("data_mode", sa.String(length=40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_agent_audit_sequence_positive"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_agent_audit_duration"),
        sa.CheckConstraint(
            "pipeline_stage IN ('lightweight_detection', 'anomaly_investigation', "
            "'network_management', 'response', 'platform_safety', 'audit')",
            name="ck_agent_audit_pipeline_stage",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'completed', 'failed', 'blocked', 'waiting', 'skipped')",
            name="ck_agent_audit_status",
        ),
        sa.CheckConstraint("data_mode = 'mock_agent_data'", name="ck_agent_audit_data_mode"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_agent_audit_events_public_id"),
    )
    op.create_index("ix_agent_audit_run_id", "agent_audit_events", ["agent_run_id"])
    op.create_index("ix_agent_audit_agent_code", "agent_audit_events", ["agent_code"])
    op.create_index("ix_agent_audit_stage", "agent_audit_events", ["pipeline_stage"])
    op.create_index("ix_agent_audit_occurred_at", "agent_audit_events", ["occurred_at"])
    op.create_index("ix_agent_audit_event_type", "agent_audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_agent_audit_event_type", table_name="agent_audit_events")
    op.drop_index("ix_agent_audit_occurred_at", table_name="agent_audit_events")
    op.drop_index("ix_agent_audit_stage", table_name="agent_audit_events")
    op.drop_index("ix_agent_audit_agent_code", table_name="agent_audit_events")
    op.drop_index("ix_agent_audit_run_id", table_name="agent_audit_events")
    op.drop_table("agent_audit_events")
    op.drop_index("ix_agent_findings_anomaly_detection_id", table_name="agent_findings")
    op.drop_constraint("fk_agent_findings_anomaly_detection", "agent_findings", type_="foreignkey")
    op.drop_column("agent_findings", "anomaly_detection_id")
    op.drop_constraint("ck_agent_runs_agent_run_type_allowed", "agent_runs", type_="check")
    op.create_check_constraint(
        "ck_agent_runs_agent_run_type_allowed",
        "agent_runs",
        "agent_type IN ('investigation_agent', 'response_agent')",
    )
