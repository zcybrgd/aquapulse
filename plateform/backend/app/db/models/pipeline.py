from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.detection import AnomalyDetection
    from app.db.models.incident import Incident
    from app.db.models.organization import Organization
    from app.db.models.zone import Zone


class PipelineSegment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_segments"
    __table_args__ = (
        UniqueConstraint("organization_id", "external_id", name="uq_pipeline_segments_org_external_id"),
        CheckConstraint("criticality_score BETWEEN 1 AND 3", name="criticality_range"),
        CheckConstraint("population_served >= 0", name="population_served_non_negative"),
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
    external_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    upstream_node: Mapped[str] = mapped_column(String(120), nullable=False)
    downstream_node: Mapped[str] = mapped_column(String(120), nullable=False)
    criticality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    population_served: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="operational")
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False),
        nullable=True,
    )

    organization: Mapped[Organization] = relationship(back_populates="pipeline_segments")
    zone: Mapped[Zone] = relationship(back_populates="pipeline_segments")
    assets: Mapped[list[Asset]] = relationship(back_populates="pipeline_segment")
    incidents: Mapped[list[Incident]] = relationship(back_populates="pipeline_segment")
    anomaly_detections: Mapped[list[AnomalyDetection]] = relationship(back_populates="pipeline_segment")
