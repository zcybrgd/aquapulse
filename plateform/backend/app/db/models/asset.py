from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.detection import AnomalyDetection
    from app.db.models.incident import Incident
    from app.db.models.organization import Organization
    from app.db.models.pipeline import PipelineSegment
    from app.db.models.device_network import DeviceNetworkSnapshot
    from app.db.models.maintenance import MaintenancePlan, MaintenanceWorkOrder
    from app.db.models.zone import Zone


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_assets_org_external_id"),
        UniqueConstraint("serial_number", name="uq_assets_serial_number"),
        CheckConstraint("asset_type IN ('sensor', 'valve', 'gateway')", name="asset_type_allowed"),
        CheckConstraint(
            "operational_status IN ('online', 'degraded', 'offline')",
            name="operational_status_allowed",
        ),
        CheckConstraint(
            "battery_pct IS NULL OR (battery_pct >= 0 AND battery_pct <= 100)",
            name="battery_pct_range",
        ),
        CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="health_score_range",
        ),
        CheckConstraint(
            "sampling_interval_seconds IS NULL OR sampling_interval_seconds > 0",
            name="sampling_interval_positive",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="longitude_range",
        ),
        CheckConstraint(
            "current_position IS NULL OR current_position IN ('open', 'closed', 'partial', 'unknown')",
            name="valve_position_allowed",
        ),
        CheckConstraint(
            "control_mode IS NULL OR control_mode IN ('manual', 'remote', 'automatic')",
            name="control_mode_allowed",
        ),
        CheckConstraint(
            "device_msisdn IS NULL OR device_msisdn ~ '^\\+[1-9][0-9]{1,14}$'",
            name="device_msisdn_e164",
        ),
        CheckConstraint(
            "location_label IS NULL OR (char_length(location_label) >= 1 AND char_length(location_label) <= 160)",
            name="location_label_length",
        ),
        Index(
            "uq_assets_device_msisdn",
            "device_msisdn",
            unique=True,
            postgresql_where=text("device_msisdn IS NOT NULL"),
        ),
    )

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
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    operational_status: Mapped[str] = mapped_column(String(40), nullable=False, default="online", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    commissioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_strength_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sampling_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_maintenance_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_maintenance_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    control_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_position: Mapped[str | None] = mapped_column(String(20), nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_msisdn: Mapped[str | None] = mapped_column(String(16), nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    location: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=True,
    )

    organization: Mapped[Organization] = relationship(back_populates="assets")
    zone: Mapped[Zone] = relationship(back_populates="assets")
    pipeline_segment: Mapped[PipelineSegment | None] = relationship(back_populates="assets")
    incidents_as_sensor: Mapped[list[Incident]] = relationship(
        back_populates="sensor",
        foreign_keys="Incident.sensor_id",
    )
    incidents_as_valve: Mapped[list[Incident]] = relationship(
        back_populates="valve",
        foreign_keys="Incident.valve_id",
    )
    anomaly_detections: Mapped[list[AnomalyDetection]] = relationship(back_populates="sensor")
    maintenance_plans: Mapped[list[MaintenancePlan]] = relationship(back_populates="asset")
    maintenance_work_orders: Mapped[list[MaintenanceWorkOrder]] = relationship(back_populates="asset")
    network_snapshots: Mapped[list[DeviceNetworkSnapshot]] = relationship(back_populates="asset")
