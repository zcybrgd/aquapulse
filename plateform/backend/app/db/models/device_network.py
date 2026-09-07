from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.db.models.asset import Asset


class DeviceNetworkSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "device_network_snapshots"
    __table_args__ = (
        CheckConstraint(
            "reachability_status IN ('reachable', 'unreachable', 'unknown', 'not_supported', 'not_checked')",
            name="reachability_allowed",
        ),
        CheckConstraint(
            "source_mode IN ('seeded_demo', 'nokia_simulator', 'nokia_live')",
            name="source_mode_allowed",
        ),
        CheckConstraint(
            "network_latitude IS NULL OR (network_latitude >= -90 AND network_latitude <= 90)",
            name="latitude_range",
        ),
        CheckConstraint(
            "network_longitude IS NULL OR (network_longitude >= -180 AND network_longitude <= 180)",
            name="longitude_range",
        ),
        CheckConstraint(
            "accuracy_radius_m IS NULL OR accuracy_radius_m >= 0",
            name="accuracy_non_negative",
        ),
        CheckConstraint(
            "(network_location_available = true AND network_latitude IS NOT NULL "
            "AND network_longitude IS NOT NULL) OR "
            "(network_location_available = false AND network_latitude IS NULL "
            "AND network_longitude IS NULL AND accuracy_radius_m IS NULL "
            "AND location_area_type IS NULL AND location_observed_at IS NULL)",
            name="location_consistency",
        ),
        Index("ix_device_network_snapshots_asset_id", "asset_id"),
        Index("ix_device_network_snapshots_retrieved_at", "retrieved_at"),
        Index("ix_device_network_snapshots_reachability", "reachability_status"),
        Index("ix_device_network_snapshots_provider_source", "provider", "source_mode"),
    )

    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    reachability_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reachable_via: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reachability_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    network_location_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    network_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_area_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    request_correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    raw_reachability_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_location_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    asset: Mapped[Asset] = relationship(back_populates="network_snapshots")
