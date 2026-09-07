from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.incident_event import IncidentTelemetry, IncidentTimelineEvent
    from app.db.models.organization import Organization
    from app.db.models.pipeline import PipelineSegment
    from app.db.models.response_task import IncidentResponseTask
    from app.db.models.maintenance import MaintenanceWorkOrder
    from app.db.models.zone import Zone


class Incident(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("severity_tier BETWEEN 1 AND 3", name="severity_tier_range"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"),
        CheckConstraint(
            "packet_loss_pct IS NULL OR (packet_loss_pct >= 0 AND packet_loss_pct <= 100)",
            name="packet_loss_range",
        ),
        CheckConstraint("population_affected >= 0", name="population_affected_non_negative"),
        CheckConstraint("estimated_water_loss_m3 >= 0", name="water_loss_non_negative"),
        CheckConstraint("estimated_loss_lps >= 0", name="loss_lps_non_negative"),
        CheckConstraint(
            "resolution_code IS NULL OR resolution_code IN ("
            "'leak_repaired', 'isolated_for_maintenance', 'sensor_fault', "
            "'planned_operation', 'false_alarm', 'monitoring_completed', 'other')",
            name="resolution_code_allowed",
        ),
        CheckConstraint(
            "status <> 'resolved' OR ("
            "resolved_at IS NOT NULL AND resolved_by IS NOT NULL "
            "AND resolution_summary IS NOT NULL AND btrim(resolution_summary) <> '')",
            name="resolved_requires_closure",
        ),
        CheckConstraint(
            "status IN ('investigating', 'awaiting_approval', 'resolved')",
            name="status_allowed",
        ),
        CheckConstraint(
            "status = 'resolved' OR ("
            "resolved_at IS NULL AND resolved_by IS NULL "
            "AND resolution_code IS NULL AND resolution_summary IS NULL)",
            name="active_clears_resolution",
        ),
    )

    incident_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[UUID] = mapped_column(
        ForeignKey("zones.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pipeline_segment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pipeline_segments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    sensor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    valve_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    severity_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    estimated_water_loss_m3: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    estimated_loss_lps: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    population_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    pressure_change_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    flow_change_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    network_condition: Mapped[str] = mapped_column(String(300), nullable=False)
    signal_strength_dbm: Mapped[int] = mapped_column(Integer, nullable=False)
    packet_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    assigned_operator: Mapped[str | None] = mapped_column(String(120), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    response_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolution_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    agent_investigation_summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(2000), nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    network_details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    organization: Mapped[Organization] = relationship(back_populates="incidents")
    zone: Mapped[Zone] = relationship(back_populates="incidents")
    pipeline_segment: Mapped[PipelineSegment | None] = relationship(back_populates="incidents")
    sensor: Mapped[Asset | None] = relationship(
        back_populates="incidents_as_sensor",
        foreign_keys=[sensor_id],
    )
    valve: Mapped[Asset | None] = relationship(
        back_populates="incidents_as_valve",
        foreign_keys=[valve_id],
    )
    telemetry_points: Mapped[list[IncidentTelemetry]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTelemetry.timestamp",
    )
    timeline_events: Mapped[list[IncidentTimelineEvent]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTimelineEvent.timestamp",
    )
    response_tasks: Mapped[list[IncidentResponseTask]] = relationship(
        back_populates="incident",
        cascade="save-update",
        order_by="IncidentResponseTask.created_at",
    )
    maintenance_work_orders: Mapped[list[MaintenanceWorkOrder]] = relationship(back_populates="incident")
