"""Maintenance Center plans, work orders, and append-only history.

Downgrade removes only Step 12 additions.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_maintenance_center"
down_revision = "0009_device_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("maintenance_type", sa.String(length=40), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("instructions", sa.String(length=4000), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "maintenance_type IN ('preventive', 'inspection', 'calibration', 'battery_replacement', 'connectivity_check', 'corrective')",
            name="ck_maintenance_plans_type_allowed",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_maintenance_plans_priority_allowed",
        ),
        sa.CheckConstraint("interval_days > 0", name="ck_maintenance_plans_interval_positive"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_maintenance_plans_asset_id", "maintenance_plans", ["asset_id"])
    op.create_index("ix_maintenance_plans_enabled", "maintenance_plans", ["enabled"])
    op.create_index("ix_maintenance_plans_next_due_at", "maintenance_plans", ["next_due_at"])

    op.create_table(
        "maintenance_work_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("maintenance_plan_id", sa.Uuid(), nullable=True),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("maintenance_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("assigned_to", sa.String(length=120), nullable=True),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(length=120), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=120), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=2000), nullable=True),
        sa.Column("completion_summary", sa.String(length=2000), nullable=True),
        sa.Column("completion_result", sa.String(length=40), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "maintenance_type IN ('preventive', 'inspection', 'calibration', 'battery_replacement', 'connectivity_check', 'corrective')",
            name="ck_maintenance_work_orders_type_allowed",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_maintenance_work_orders_priority_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name="ck_maintenance_work_orders_status_allowed",
        ),
        sa.CheckConstraint(
            "completion_result IS NULL OR completion_result IN ("
            "'completed_successfully', 'follow_up_required', 'asset_repaired', "
            "'asset_replaced', 'no_fault_found', 'unable_to_complete', 'other')",
            name="ck_maintenance_work_orders_result_allowed",
        ),
        sa.CheckConstraint(
            "status <> 'completed' OR ("
            "completed_at IS NOT NULL AND completed_by IS NOT NULL "
            "AND completion_result IS NOT NULL "
            "AND completion_summary IS NOT NULL AND btrim(completion_summary) <> '')",
            name="ck_maintenance_work_orders_completed_requires_meta",
        ),
        sa.CheckConstraint(
            "status <> 'cancelled' OR ("
            "cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL "
            "AND cancellation_reason IS NOT NULL AND btrim(cancellation_reason) <> '')",
            name="ck_maintenance_work_orders_cancelled_requires_meta",
        ),
        sa.CheckConstraint(
            "status <> 'completed' OR (cancelled_at IS NULL AND cancelled_by IS NULL AND cancellation_reason IS NULL)",
            name="ck_maintenance_work_orders_completed_clears_cancel",
        ),
        sa.CheckConstraint(
            "status <> 'cancelled' OR (completed_at IS NULL AND completed_by IS NULL "
            "AND completion_result IS NULL AND completion_summary IS NULL)",
            name="ck_maintenance_work_orders_cancelled_clears_complete",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'cancelled') OR ("
            "completed_at IS NULL AND completed_by IS NULL "
            "AND completion_result IS NULL AND completion_summary IS NULL "
            "AND cancelled_at IS NULL AND cancelled_by IS NULL AND cancellation_reason IS NULL)",
            name="ck_maintenance_work_orders_active_clears_terminal",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["maintenance_plan_id"], ["maintenance_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_maintenance_work_orders_asset_id", "maintenance_work_orders", ["asset_id"])
    op.create_index("ix_maintenance_work_orders_plan_id", "maintenance_work_orders", ["maintenance_plan_id"])
    op.create_index("ix_maintenance_work_orders_incident_id", "maintenance_work_orders", ["incident_id"])
    op.create_index("ix_maintenance_work_orders_status", "maintenance_work_orders", ["status"])
    op.create_index("ix_maintenance_work_orders_due_at", "maintenance_work_orders", ["due_at"])
    op.create_index("ix_maintenance_work_orders_priority", "maintenance_work_orders", ["priority"])

    op.create_table(
        "maintenance_work_order_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=True),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("actor_name", sa.String(length=120), nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "event_type IN ("
            "'work_order_created', 'work_order_assigned', 'work_order_rescheduled', "
            "'work_started', 'note_added', 'work_completed', 'work_cancelled', "
            "'plan_created', 'plan_updated', 'plan_disabled')",
            name="ck_maintenance_events_type_allowed",
        ),
        sa.CheckConstraint(
            "work_order_id IS NOT NULL OR plan_id IS NOT NULL",
            name="ck_maintenance_events_has_subject",
        ),
        sa.ForeignKeyConstraint(["work_order_id"], ["maintenance_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["maintenance_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_maintenance_events_work_order_id", "maintenance_work_order_events", ["work_order_id"])
    op.create_index("ix_maintenance_events_plan_id", "maintenance_work_order_events", ["plan_id"])
    op.create_index("ix_maintenance_events_created_at", "maintenance_work_order_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_maintenance_events_created_at", table_name="maintenance_work_order_events")
    op.drop_index("ix_maintenance_events_plan_id", table_name="maintenance_work_order_events")
    op.drop_index("ix_maintenance_events_work_order_id", table_name="maintenance_work_order_events")
    op.drop_table("maintenance_work_order_events")
    op.drop_index("ix_maintenance_work_orders_priority", table_name="maintenance_work_orders")
    op.drop_index("ix_maintenance_work_orders_due_at", table_name="maintenance_work_orders")
    op.drop_index("ix_maintenance_work_orders_status", table_name="maintenance_work_orders")
    op.drop_index("ix_maintenance_work_orders_incident_id", table_name="maintenance_work_orders")
    op.drop_index("ix_maintenance_work_orders_plan_id", table_name="maintenance_work_orders")
    op.drop_index("ix_maintenance_work_orders_asset_id", table_name="maintenance_work_orders")
    op.drop_table("maintenance_work_orders")
    op.drop_index("ix_maintenance_plans_next_due_at", table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_enabled", table_name="maintenance_plans")
    op.drop_index("ix_maintenance_plans_asset_id", table_name="maintenance_plans")
    op.drop_table("maintenance_plans")
