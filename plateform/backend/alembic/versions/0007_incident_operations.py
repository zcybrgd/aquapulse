"""Operations Center workflow for incidents.

Adds operational state columns, response tasks, and structured timeline
fields. Does not change existing incident public IDs, telemetry, or evidence.
Legacy `monitoring` statuses are preserved.
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_incident_operations"
down_revision = "0006_detection_investigation"
branch_labels = None
depends_on = None

RESOLUTION_CODES = (
    "leak_repaired",
    "isolated_for_maintenance",
    "sensor_fault",
    "planned_operation",
    "false_alarm",
    "monitoring_completed",
    "other",
)


def upgrade() -> None:
    op.add_column("incidents", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("acknowledged_by", sa.String(length=120), nullable=True))
    op.add_column("incidents", sa.Column("response_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("resolved_by", sa.String(length=120), nullable=True))
    op.add_column("incidents", sa.Column("resolution_code", sa.String(length=40), nullable=True))
    op.add_column("incidents", sa.Column("resolution_summary", sa.String(length=2000), nullable=True))

    op.create_index("ix_incidents_acknowledged_by", "incidents", ["acknowledged_by"])
    op.create_index("ix_incidents_resolved_at", "incidents", ["resolved_at"])

    op.execute(
        sa.text(
            """
            UPDATE incidents
            SET
                resolved_at = COALESCE(resolved_at, updated_at),
                resolved_by = COALESCE(resolved_by, assigned_operator, 'Seed Operator'),
                resolution_summary = COALESCE(NULLIF(TRIM(resolution_summary), ''), current_summary),
                resolution_code = CASE
                    WHEN status = 'false_alarm' THEN 'false_alarm'
                    ELSE COALESCE(resolution_code, 'other')
                END
            WHERE status IN ('resolved', 'false_alarm')
            """
        )
    )

    codes = ", ".join(f"'{code}'" for code in RESOLUTION_CODES)
    op.create_check_constraint(
        "ck_incidents_resolution_code_allowed",
        "incidents",
        f"resolution_code IS NULL OR resolution_code IN ({codes})",
    )
    op.create_check_constraint(
        "ck_incidents_resolved_requires_closure",
        "incidents",
        "status <> 'resolved' OR ("
        "resolved_at IS NOT NULL AND resolved_by IS NOT NULL "
        "AND resolution_summary IS NOT NULL AND btrim(resolution_summary) <> '')",
    )
    op.create_check_constraint(
        "ck_incidents_false_alarm_requires_code",
        "incidents",
        "status <> 'false_alarm' OR ("
        "resolution_code = 'false_alarm' AND resolved_at IS NOT NULL "
        "AND resolved_by IS NOT NULL AND resolution_summary IS NOT NULL "
        "AND btrim(resolution_summary) <> '')",
    )
    op.create_check_constraint(
        "ck_incidents_active_clears_resolution",
        "incidents",
        "status IN ('resolved', 'false_alarm') OR ("
        "resolved_at IS NULL AND resolved_by IS NULL "
        "AND resolution_code IS NULL AND resolution_summary IS NULL)",
    )

    op.add_column(
        "incident_timeline_events",
        sa.Column("actor_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "incident_timeline_events",
        sa.Column("response_task_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_incident_timeline_events_response_task_id",
        "incident_timeline_events",
        ["response_task_id"],
    )

    op.create_table(
        "incident_response_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("assigned_to", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(length=120), nullable=True),
        sa.Column("completion_note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_incident_response_tasks"),
        sa.UniqueConstraint("public_id", name="uq_incident_response_tasks_public_id"),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_incident_response_tasks_incident_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('todo', 'in_progress', 'completed', 'cancelled')",
            name="ck_incident_response_tasks_task_status_allowed",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_incident_response_tasks_task_priority_allowed",
        ),
        sa.CheckConstraint(
            "status <> 'completed' OR (completed_at IS NOT NULL AND completed_by IS NOT NULL)",
            name="ck_incident_response_tasks_completed_requires_meta",
        ),
    )
    op.create_index("ix_incident_response_tasks_incident_id", "incident_response_tasks", ["incident_id"])
    op.create_index("ix_incident_response_tasks_status", "incident_response_tasks", ["status"])
    op.create_index("ix_incident_response_tasks_due_at", "incident_response_tasks", ["due_at"])

    op.create_foreign_key(
        "fk_timeline_events_response_task",
        "incident_timeline_events",
        "incident_response_tasks",
        ["response_task_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_timeline_events_response_task", "incident_timeline_events", type_="foreignkey")
    op.drop_index("ix_incident_timeline_events_response_task_id", table_name="incident_timeline_events")
    op.drop_column("incident_timeline_events", "response_task_id")
    op.drop_column("incident_timeline_events", "actor_name")

    op.drop_index("ix_incident_response_tasks_due_at", table_name="incident_response_tasks")
    op.drop_index("ix_incident_response_tasks_status", table_name="incident_response_tasks")
    op.drop_index("ix_incident_response_tasks_incident_id", table_name="incident_response_tasks")
    op.drop_table("incident_response_tasks")

    op.drop_constraint("ck_incidents_active_clears_resolution", "incidents", type_="check")
    op.drop_constraint("ck_incidents_false_alarm_requires_code", "incidents", type_="check")
    op.drop_constraint("ck_incidents_resolved_requires_closure", "incidents", type_="check")
    op.drop_constraint("ck_incidents_resolution_code_allowed", "incidents", type_="check")
    op.drop_index("ix_incidents_resolved_at", table_name="incidents")
    op.drop_index("ix_incidents_acknowledged_by", table_name="incidents")
    op.drop_column("incidents", "resolution_summary")
    op.drop_column("incidents", "resolution_code")
    op.drop_column("incidents", "resolved_by")
    op.drop_column("incidents", "resolved_at")
    op.drop_column("incidents", "response_started_at")
    op.drop_column("incidents", "acknowledged_by")
    op.drop_column("incidents", "acknowledged_at")
