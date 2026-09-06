from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.incident import Incident
    from app.db.models.organization import Organization
    from app.db.models.pipeline import PipelineSegment


class Zone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_zones_org_code"),)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    boundary: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=True,
    )

    organization: Mapped[Organization] = relationship(back_populates="zones")
    pipeline_segments: Mapped[list[PipelineSegment]] = relationship(back_populates="zone")
    assets: Mapped[list[Asset]] = relationship(back_populates="zone")
    incidents: Mapped[list[Incident]] = relationship(back_populates="zone")
