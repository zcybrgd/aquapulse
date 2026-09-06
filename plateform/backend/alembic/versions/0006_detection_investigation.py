"""Human investigation workflow for anomaly detections.

Adds append-only investigation events and workflow columns on
anomaly_detections. Does not modify existing detection evidence or public IDs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_detection_investigation"
down_revision = "0005_anomaly_detections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "anomaly_detections",
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "anomaly_detections",
        sa.Column("review_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "anomaly_detections",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "anomaly_detections",
        sa.Column("dismissal_reason", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "anomaly_detections",
        sa.Column("merged_into_detection_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "anomaly_detections",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_anomaly_detections_merged_into",
        "anomaly_detections",
        "anomaly_detections",
        ["merged_into_detection_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_anomaly_detections_merged_into_detection_id",
        "anomaly_detections",
        ["merged_into_detection_id"],
    )
    op.create_index(
        "ix_anomaly_detections_reviewed_by",
        "anomaly_detections",
        ["reviewed_by"],
    )
    op.create_check_constraint(
        "ck_anomaly_detections_dismissed_requires_reason",
        "anomaly_detections",
        "status <> 'dismissed' OR dismissal_reason IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_anomaly_detections_merged_requires_target",
        "anomaly_detections",
        "status <> 'merged' OR merged_into_detection_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_anomaly_detections_merge_not_self",
        "anomaly_detections",
        "merged_into_detection_id IS NULL OR merged_into_detection_id <> id",
    )
    op.create_check_constraint(
        "ck_anomaly_detections_dismissal_reason_allowed",
        "anomaly_detections",
        "dismissal_reason IS NULL OR dismissal_reason IN ("
        "'false_positive', 'sensor_fault', 'planned_operation', "
        "'duplicate', 'insufficient_evidence', 'other')",
    )

    op.create_table(
        "detection_investigation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("detection_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=True),
        sa.Column("actor_name", sa.String(length=120), nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('review_started', 'note_added', 'dismissed', "
            "'reopened', 'merged', 'promoted')",
            name="ck_detection_investigation_events_event_type_allowed",
        ),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('new', 'queued', 'under_review', 'dismissed', 'promoted', 'merged')",
            name="ck_detection_investigation_events_from_status_allowed",
        ),
        sa.CheckConstraint(
            "to_status IS NULL OR to_status IN "
            "('new', 'queued', 'under_review', 'dismissed', 'promoted', 'merged')",
            name="ck_detection_investigation_events_to_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["detection_id"],
            ["anomaly_detections.id"],
            name="fk_detection_investigation_events_detection_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_detection_investigation_events"),
        sa.UniqueConstraint("public_id", name="uq_detection_investigation_events_public_id"),
    )
    op.create_index(
        "ix_detection_investigation_events_detection_id",
        "detection_investigation_events",
        ["detection_id"],
    )
    op.create_index(
        "ix_detection_investigation_events_detection_id_created_at",
        "detection_investigation_events",
        ["detection_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_detection_investigation_events_detection_id_created_at",
        table_name="detection_investigation_events",
    )
    op.drop_index(
        "ix_detection_investigation_events_detection_id",
        table_name="detection_investigation_events",
    )
    op.drop_table("detection_investigation_events")
    op.drop_constraint(
        "ck_anomaly_detections_dismissal_reason_allowed",
        "anomaly_detections",
        type_="check",
    )
    op.drop_constraint(
        "ck_anomaly_detections_merge_not_self",
        "anomaly_detections",
        type_="check",
    )
    op.drop_constraint(
        "ck_anomaly_detections_merged_requires_target",
        "anomaly_detections",
        type_="check",
    )
    op.drop_constraint(
        "ck_anomaly_detections_dismissed_requires_reason",
        "anomaly_detections",
        type_="check",
    )
    op.drop_index("ix_anomaly_detections_reviewed_by", table_name="anomaly_detections")
    op.drop_index("ix_anomaly_detections_merged_into_detection_id", table_name="anomaly_detections")
    op.drop_constraint(
        "fk_anomaly_detections_merged_into",
        "anomaly_detections",
        type_="foreignkey",
    )
    op.drop_column("anomaly_detections", "resolved_at")
    op.drop_column("anomaly_detections", "merged_into_detection_id")
    op.drop_column("anomaly_detections", "dismissal_reason")
    op.drop_column("anomaly_detections", "dismissed_at")
    op.drop_column("anomaly_detections", "review_started_at")
    op.drop_column("anomaly_detections", "reviewed_by")
