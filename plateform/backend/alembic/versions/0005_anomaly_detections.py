"""Deterministic anomaly detections, versioned rules, and structured evidence.

Initial rule thresholds stored by the seed are engineering demo values and
require calibration with field data. They are not a leak confirmation.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_anomaly_detections"
down_revision = "0004_timescaledb_sensor_readings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detection_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("rule_type", sa.String(length=40), nullable=False),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("operator", sa.String(length=40), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("secondary_threshold", sa.Float(), nullable=True),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("minimum_points", sa.Integer(), nullable=False),
        sa.Column("severity_weight", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "rule_type IN ('rate_of_change', 'absolute_threshold', 'connectivity', "
            "'missing_telemetry', 'cross_metric')",
            name="ck_detection_rules_rule_type_allowed",
        ),
        sa.CheckConstraint("window_minutes > 0", name="ck_detection_rules_window_minutes_positive"),
        sa.CheckConstraint("minimum_points > 0", name="ck_detection_rules_minimum_points_positive"),
        sa.CheckConstraint(
            "severity_weight >= 0 AND severity_weight <= 1",
            name="ck_detection_rules_severity_weight_range",
        ),
        sa.CheckConstraint("version > 0", name="ck_detection_rules_version_positive"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_detection_rules_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_detection_rules"),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            "version",
            name="uq_detection_rules_org_code_version",
        ),
    )
    op.create_index("ix_detection_rules_organization_id", "detection_rules", ["organization_id"])
    op.create_index(
        "uq_detection_rules_org_code_enabled",
        "detection_rules",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=sa.text("enabled IS TRUE"),
    )

    op.create_table(
        "anomaly_detections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("detection_number", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("sensor_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_segment_id", sa.Uuid(), nullable=True),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("trigger_reason", sa.String(length=500), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reading_count", sa.Integer(), nullable=False),
        sa.Column("correlation_key", sa.String(length=200), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("data_mode", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('new', 'queued', 'under_review', 'dismissed', 'promoted', 'merged')",
            name="ck_anomaly_detections_status_allowed",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_anomaly_detections_priority_allowed",
        ),
        sa.CheckConstraint(
            "anomaly_score >= 0 AND anomaly_score <= 1",
            name="ck_anomaly_detections_anomaly_score_range",
        ),
        sa.CheckConstraint("window_start <= window_end", name="ck_anomaly_detections_window_order"),
        sa.CheckConstraint("reading_count >= 0", name="ck_anomaly_detections_reading_count_non_negative"),
        sa.CheckConstraint(
            "status <> 'promoted' OR incident_id IS NOT NULL",
            name="ck_anomaly_detections_promoted_requires_incident",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_anomaly_detections_incident_id_incidents",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_anomaly_detections_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_segment_id"],
            ["pipeline_segments.id"],
            name="fk_anomaly_detections_pipeline_segment_id_pipeline_segments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["detection_rules.id"],
            name="fk_anomaly_detections_rule_id_detection_rules",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sensor_id"],
            ["assets.id"],
            name="fk_anomaly_detections_sensor_id_assets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_anomaly_detections"),
        sa.UniqueConstraint("detection_number", name="uq_anomaly_detections_detection_number"),
    )
    op.create_index("ix_anomaly_detections_organization_id", "anomaly_detections", ["organization_id"])
    op.create_index(
        "ix_anomaly_detections_status_detected_at",
        "anomaly_detections",
        ["status", "detected_at"],
    )
    op.create_index(
        "ix_anomaly_detections_sensor_detected_at",
        "anomaly_detections",
        ["sensor_id", "detected_at"],
    )
    op.create_index(
        "ix_anomaly_detections_priority_detected_at",
        "anomaly_detections",
        ["priority", "detected_at"],
    )
    op.create_index("ix_anomaly_detections_incident_id", "anomaly_detections", ["incident_id"])
    op.create_index("ix_anomaly_detections_correlation_key", "anomaly_detections", ["correlation_key"])

    op.create_table(
        "detection_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("detection_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("reading_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reading_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["detection_id"],
            ["anomaly_detections.id"],
            name="fk_detection_evidence_detection_id_anomaly_detections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_detection_evidence"),
    )
    op.create_index("ix_detection_evidence_detection_id", "detection_evidence", ["detection_id"])
    op.create_index("ix_detection_evidence_metric", "detection_evidence", ["metric"])


def downgrade() -> None:
    op.drop_index("ix_detection_evidence_metric", table_name="detection_evidence")
    op.drop_index("ix_detection_evidence_detection_id", table_name="detection_evidence")
    op.drop_table("detection_evidence")
    op.drop_index("ix_anomaly_detections_correlation_key", table_name="anomaly_detections")
    op.drop_index("ix_anomaly_detections_incident_id", table_name="anomaly_detections")
    op.drop_index("ix_anomaly_detections_priority_detected_at", table_name="anomaly_detections")
    op.drop_index("ix_anomaly_detections_sensor_detected_at", table_name="anomaly_detections")
    op.drop_index("ix_anomaly_detections_status_detected_at", table_name="anomaly_detections")
    op.drop_index("ix_anomaly_detections_organization_id", table_name="anomaly_detections")
    op.drop_table("anomaly_detections")
    op.drop_index("uq_detection_rules_org_code_enabled", table_name="detection_rules")
    op.drop_index("ix_detection_rules_organization_id", table_name="detection_rules")
    op.drop_table("detection_rules")
