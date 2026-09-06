from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.organization import Organization


class SensorReading(Base):
    """TimescaleDB hypertable of simulated sensor measurements. Partitioned by time."""

    __tablename__ = "sensor_readings"
    __table_args__ = (
        CheckConstraint(
            "("
            "pressure_kpa IS NOT NULL OR flow_lps IS NOT NULL OR temperature_c IS NOT NULL "
            "OR signal_strength_dbm IS NOT NULL OR packet_loss_pct IS NOT NULL "
            "OR battery_pct IS NOT NULL"
            ")",
            name="sensor_readings_has_measurement",
        ),
        CheckConstraint(
            "packet_loss_pct IS NULL OR (packet_loss_pct >= 0 AND packet_loss_pct <= 100)",
            name="sensor_readings_packet_loss_range",
        ),
        CheckConstraint(
            "battery_pct IS NULL OR (battery_pct >= 0 AND battery_pct <= 100)",
            name="sensor_readings_battery_range",
        ),
        CheckConstraint(
            "received_at >= time - INTERVAL '1 hour'",
            name="sensor_readings_received_not_unreasonably_early",
        ),
        UniqueConstraint(
            "sensor_id",
            "time",
            "source_message_id",
            name="uq_sensor_readings_sensor_time_source",
        ),
        Index("ix_sensor_readings_sensor_time", "sensor_id", "time", postgresql_ops={"time": "DESC"}),
        Index(
            "ix_sensor_readings_org_time",
            "organization_id",
            "time",
            postgresql_ops={"time": "DESC"},
        ),
        Index("ix_sensor_readings_sensor_source", "sensor_id", "source_message_id"),
    )

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    sensor_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_message_id: Mapped[str] = mapped_column(String(120), nullable=False)
    pressure_kpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    flow_lps: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_strength_dbm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    packet_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    sensor: Mapped[Asset] = relationship()
    organization: Mapped[Organization] = relationship()
