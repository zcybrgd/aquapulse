"""Agent integration readiness tables.

Adds disabled-by-default agent integrations, run history, advisory findings,
response recommendations, and identity mappings. Does not enable execution,
CAMARA, notifications, or physical commands.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_agent_integration_readiness"
down_revision = "0007_incident_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("contract_version", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="disabled"),
        sa.Column("health_status", sa.String(length=20), nullable=False, server_default="disabled"),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("mode IN ('disabled', 'mock', 'remote')", name="ck_agent_integrations_agent_mode_allowed"),
        sa.CheckConstraint(
            "health_status IN ('unknown', 'disabled', 'healthy', 'unhealthy', 'unreachable')",
            name="ck_agent_integrations_agent_health_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_integrations"),
        sa.UniqueConstraint("agent_code", name="uq_agent_integrations_agent_code"),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("agent_integration_id", sa.Uuid(), nullable=False),
        sa.Column("agent_type", sa.String(length=40), nullable=False),
        sa.Column("contract_version", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("correlation_id", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_public_id", sa.String(length=80), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("mapping_warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("data_mode", sa.String(length=40), nullable=False, server_default="simulated"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('pending', 'validating', 'ready', 'running', 'succeeded', 'failed', 'rejected', 'cancelled')",
            name="ck_agent_runs_agent_run_status_allowed",
        ),
        sa.CheckConstraint(
            "agent_type IN ('investigation_agent', 'response_agent')",
            name="ck_agent_runs_agent_run_type_allowed",
        ),
        sa.ForeignKeyConstraint(["agent_integration_id"], ["agent_integrations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
        sa.UniqueConstraint("public_id", name="uq_agent_runs_public_id"),
    )
    op.create_index("ix_agent_runs_agent_integration_id", "agent_runs", ["agent_integration_id"])
    op.create_index("ix_agent_runs_idempotency_key", "agent_runs", ["idempotency_key"])
    op.create_index("ix_agent_runs_correlation_id", "agent_runs", ["correlation_id"])

    op.create_table(
        "agent_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="investigation_agent"),
        sa.Column("external_anomaly_id", sa.String(length=120), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("classification", sa.String(length=60), nullable=False),
        sa.Column("severity_tier", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("external_cluster_id", sa.String(length=120), nullable=True),
        sa.Column("external_segment_id", sa.String(length=120), nullable=True),
        sa.Column("external_valve_id", sa.String(length=120), nullable=True),
        sa.Column("mapped_detection_id", sa.String(length=32), nullable=True),
        sa.Column("mapped_sensor_id", sa.String(length=80), nullable=True),
        sa.Column("mapped_segment_id", sa.String(length=80), nullable=True),
        sa.Column("mapped_valve_id", sa.String(length=80), nullable=True),
        sa.Column("network_status", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("physical_deviations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("criticality_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("operator_justification", sa.String(length=4000), nullable=True),
        sa.Column("mapping_status", sa.String(length=20), nullable=False, server_default="unmapped"),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="unread"),
        sa.Column("raw_finding", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "classification IN ('confirmed_anomaly', 'confirmed_instrument_fault')",
            name="ck_agent_findings_finding_classification_allowed",
        ),
        sa.CheckConstraint("severity_tier BETWEEN 1 AND 3", name="ck_agent_findings_finding_severity_range"),
        sa.CheckConstraint(
            "mapping_status IN ('mapped', 'unmapped', 'partial')",
            name="ck_agent_findings_finding_mapping_status_allowed",
        ),
        sa.CheckConstraint(
            "review_status IN ('unread', 'reviewed', 'dismissed')",
            name="ck_agent_findings_finding_review_status_allowed",
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_findings"),
        sa.UniqueConstraint("provider", "external_anomaly_id", name="uq_agent_findings_provider_anomaly"),
    )
    op.create_index("ix_agent_findings_agent_run_id", "agent_findings", ["agent_run_id"])

    op.create_table(
        "agent_response_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="response_agent"),
        sa.Column("external_result_id", sa.String(length=120), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("external_incident_id", sa.String(length=120), nullable=True),
        sa.Column("external_cluster_id", sa.String(length=120), nullable=True),
        sa.Column("external_device_id", sa.String(length=120), nullable=True),
        sa.Column("mapped_incident_number", sa.String(length=32), nullable=True),
        sa.Column("mapped_device_id", sa.String(length=80), nullable=True),
        sa.Column("severity_tier", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("reachability", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("valve_command_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("valve_command_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("human_override_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("human_override_response", sa.String(length=2000), nullable=True),
        sa.Column("reasoning_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("safety_status", sa.String(length=40), nullable=False, server_default="advisory"),
        sa.Column("raw_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "decision IN ('LOG_ONLY', 'ALERT_AND_AWAIT', 'AUTONOMOUS_ISOLATE', 'ESCALATE_UNREACHABLE')",
            name="ck_agent_response_recommendations_recommendation_decision_allowed",
        ),
        sa.CheckConstraint("severity_tier BETWEEN 1 AND 3", name="ck_agent_response_recommendations_recommendation_severity_range"),
        sa.CheckConstraint(
            "safety_status IN ('advisory', 'blocked', 'agent_reported_unverified')",
            name="ck_agent_response_recommendations_recommendation_safety_allowed",
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_response_recommendations"),
        sa.UniqueConstraint("provider", "external_result_id", name="uq_agent_recs_provider_result"),
    )
    op.create_index("ix_agent_recs_agent_run_id", "agent_response_recommendations", ["agent_run_id"])

    op.create_table(
        "integration_identity_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("internal_entity_type", sa.String(length=40), nullable=False),
        sa.Column("internal_public_id", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "entity_type IN ('sensor_cluster', 'sensor', 'segment', 'valve', 'device', 'incident', 'detection')",
            name="ck_integration_identity_mappings_identity_entity_type_allowed",
        ),
        sa.CheckConstraint(
            "internal_entity_type IN ('sensor_cluster', 'sensor', 'segment', 'valve', 'device', 'incident', 'detection')",
            name="ck_integration_identity_mappings_identity_internal_type_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_integration_identity_mappings"),
        sa.UniqueConstraint("provider", "entity_type", "external_id", name="uq_identity_mapping_provider_type_ext"),
    )
    op.create_index(
        "ix_identity_mappings_internal",
        "integration_identity_mappings",
        ["internal_entity_type", "internal_public_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO agent_integrations (id, agent_code, display_name, contract_version, enabled, mode, health_status)
            VALUES
              (gen_random_uuid(), 'investigation_agent', 'Investigation Agent', '1.0', false, 'disabled', 'disabled'),
              (gen_random_uuid(), 'response_agent', 'Response Agent', '1.0', false, 'disabled', 'disabled')
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_identity_mappings_internal", table_name="integration_identity_mappings")
    op.drop_table("integration_identity_mappings")
    op.drop_index("ix_agent_recs_agent_run_id", table_name="agent_response_recommendations")
    op.drop_table("agent_response_recommendations")
    op.drop_index("ix_agent_findings_agent_run_id", table_name="agent_findings")
    op.drop_table("agent_findings")
    op.drop_index("ix_agent_runs_correlation_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_idempotency_key", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_integration_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_table("agent_integrations")
