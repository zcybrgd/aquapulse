from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.db.models.incident import Incident
    from app.db.models.response_task import IncidentResponseTask


class IncidentTelemetry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_telemetry"
    __table_args__ = (
        Index("ix_incident_telemetry_incident_id_timestamp", "incident_id", "timestamp"),
        CheckConstraint(
            "packet_loss_pct >= 0 AND packet_loss_pct <= 100",
            name="telemetry_packet_loss_range",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pressure: Mapped[float] = mapped_column(Float, nullable=False)
    flow_rate: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)
    is_detection_point: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    incident: Mapped[Incident] = relationship(back_populates="telemetry_points")


class IncidentTimelineEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "incident_timeline_events"
    __table_args__ = (
        Index("ix_incident_timeline_events_incident_id_timestamp", "incident_id", "timestamp"),
        CheckConstraint(
            "source IN ('detector', 'agent', 'network', 'operator', 'system')",
            name="timeline_source_allowed",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    actor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    response_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incident_response_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    incident: Mapped[Incident] = relationship(back_populates="timeline_events")
    response_task: Mapped[IncidentResponseTask | None] = relationship()
