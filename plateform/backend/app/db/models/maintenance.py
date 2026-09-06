from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.incident import Incident


class MaintenancePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_plans"
    __table_args__ = (
        CheckConstraint(
            "maintenance_type IN ('preventive', 'inspection', 'calibration', "
            "'battery_replacement', 'connectivity_check', 'corrective')",
            name="maintenance_plans_type_allowed",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="maintenance_plans_priority_allowed",
        ),
        CheckConstraint("interval_days > 0", name="maintenance_plans_interval_positive"),
    )

    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(40), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    instructions: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="maintenance_plans")
    work_orders: Mapped[list[MaintenanceWorkOrder]] = relationship(back_populates="plan")
    events: Mapped[list[MaintenanceWorkOrderEvent]] = relationship(back_populates="plan")


class MaintenanceWorkOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_work_orders"
    __table_args__ = (
        CheckConstraint(
            "maintenance_type IN ('preventive', 'inspection', 'calibration', "
            "'battery_replacement', 'connectivity_check', 'corrective')",
            name="maintenance_work_orders_type_allowed",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="maintenance_work_orders_priority_allowed",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name="maintenance_work_orders_status_allowed",
        ),
        CheckConstraint(
            "completion_result IS NULL OR completion_result IN ("
            "'completed_successfully', 'follow_up_required', 'asset_repaired', "
            "'asset_replaced', 'no_fault_found', 'unable_to_complete', 'other')",
            name="maintenance_work_orders_result_allowed",
        ),
        CheckConstraint(
            "status <> 'completed' OR ("
            "completed_at IS NOT NULL AND completed_by IS NOT NULL "
            "AND completion_result IS NOT NULL "
            "AND completion_summary IS NOT NULL AND btrim(completion_summary) <> '')",
            name="maintenance_work_orders_completed_requires_meta",
        ),
        CheckConstraint(
            "status <> 'cancelled' OR ("
            "cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL "
            "AND cancellation_reason IS NOT NULL AND btrim(cancellation_reason) <> '')",
            name="maintenance_work_orders_cancelled_requires_meta",
        ),
        CheckConstraint(
            "status <> 'completed' OR (cancelled_at IS NULL AND cancelled_by IS NULL AND cancellation_reason IS NULL)",
            name="maintenance_work_orders_completed_clears_cancel",
        ),
        CheckConstraint(
            "status <> 'cancelled' OR (completed_at IS NULL AND completed_by IS NULL "
            "AND completion_result IS NULL AND completion_summary IS NULL)",
            name="maintenance_work_orders_cancelled_clears_complete",
        ),
        CheckConstraint(
            "status IN ('completed', 'cancelled') OR ("
            "completed_at IS NULL AND completed_by IS NULL "
            "AND completion_result IS NULL AND completion_summary IS NULL "
            "AND cancelled_at IS NULL AND cancelled_by IS NULL AND cancellation_reason IS NULL)",
            name="maintenance_work_orders_active_clears_terminal",
        ),
    )

    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    maintenance_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("maintenance_plans.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    maintenance_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    assigned_to: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    completion_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    completion_result: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="maintenance_work_orders")
    plan: Mapped[MaintenancePlan | None] = relationship(back_populates="work_orders")
    incident: Mapped[Incident | None] = relationship(back_populates="maintenance_work_orders")
    events: Mapped[list[MaintenanceWorkOrderEvent]] = relationship(
        back_populates="work_order",
        order_by="MaintenanceWorkOrderEvent.created_at",
    )


class MaintenanceWorkOrderEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only maintenance history. Do not update or delete rows."""

    __tablename__ = "maintenance_work_order_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'work_order_created', 'work_order_assigned', 'work_order_rescheduled', "
            "'work_started', 'note_added', 'work_completed', 'work_cancelled', "
            "'plan_created', 'plan_updated', 'plan_disabled')",
            name="maintenance_events_type_allowed",
        ),
        CheckConstraint(
            "work_order_id IS NOT NULL OR plan_id IS NOT NULL",
            name="maintenance_events_has_subject",
        ),
    )

    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    work_order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("maintenance_work_orders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("maintenance_plans.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    work_order: Mapped[MaintenanceWorkOrder | None] = relationship(back_populates="events")
    plan: Mapped[MaintenancePlan | None] = relationship(back_populates="events")
