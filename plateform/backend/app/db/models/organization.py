from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.detection import AnomalyDetection, DetectionRule
    from app.db.models.incident import Incident
    from app.db.models.pipeline import PipelineSegment
    from app.db.models.zone import Zone


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    zones: Mapped[list[Zone]] = relationship(back_populates="organization")
    pipeline_segments: Mapped[list[PipelineSegment]] = relationship(back_populates="organization")
    assets: Mapped[list[Asset]] = relationship(back_populates="organization")
    incidents: Mapped[list[Incident]] = relationship(back_populates="organization")
    detection_rules: Mapped[list[DetectionRule]] = relationship(back_populates="organization")
    anomaly_detections: Mapped[list[AnomalyDetection]] = relationship(back_populates="organization")
