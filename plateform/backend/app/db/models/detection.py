from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.db.models.asset import Asset
    from app.db.models.incident import Incident
    from app.db.models.organization import Organization
    from app.db.models.pipeline import PipelineSegment


RULE_TYPES = (
    "rate_of_change",
    "absolute_threshold",
    "connectivity",
    "missing_telemetry",
    "cross_metric",
)

DETECTION_STATUSES = (
    "new",
    "queued",
    "under_review",
    "dismissed",
    "promoted",
    "merged",
)

DETECTION_PRIORITIES = ("low", "medium", "high", "critical")

INVESTIGATION_EVENT_TYPES = (
    "review_started",
    "note_added",
    "dismissed",
    "reopened",
    "merged",
    "promoted",
)

DISMISSAL_REASONS = (
    "false_positive",
    "sensor_fault",
    "planned_operation",
    "duplicate",
    "insufficient_evidence",
    "other",
)


class DetectionRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "detection_rules"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_detection_rules_org_code_version"),
        CheckConstraint(
            "rule_type IN ('rate_of_change', 'absolute_threshold', 'connectivity', "
            "'missing_telemetry', 'cross_metric')",
            name="rule_type_allowed",
        ),
        CheckConstraint("window_minutes > 0", name="window_minutes_positive"),
        CheckConstraint("minimum_points > 0", name="minimum_points_positive"),
        CheckConstraint("severity_weight >= 0 AND severity_weight <= 1", name="severity_weight_range"),
        CheckConstraint("version > 0", name="version_positive"),
        Index(
            "uq_detection_rules_org_code_enabled",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=text("enabled IS TRUE"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(40), nullable=False)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    secondary_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    window_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_points: Mapped[int] = mapped_column(Integer, nullable=False)
    severity_weight: Mapped[float] = mapped_column(Float, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    organization: Mapped[Organization] = relationship(back_populates="detection_rules")
    detections: Mapped[list[AnomalyDetection]] = relationship(back_populates="rule")


class AnomalyDetection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "anomaly_detections"
    __table_args__ = (
        UniqueConstraint("detection_number", name="uq_anomaly_detections_detection_number"),
        CheckConstraint(
            "status IN ('new', 'queued', 'under_review', 'dismissed', 'promoted', 'merged')",
            name="status_allowed",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="priority_allowed",
        ),
        CheckConstraint("anomaly_score >= 0 AND anomaly_score <= 1", name="anomaly_score_range"),
        CheckConstraint("window_start <= window_end", name="window_order"),
        CheckConstraint("reading_count >= 0", name="reading_count_non_negative"),
        CheckConstraint(
            "status <> 'promoted' OR incident_id IS NOT NULL",
            name="promoted_requires_incident",
        ),
        CheckConstraint(
            "status <> 'dismissed' OR dismissal_reason IS NOT NULL",
            name="dismissed_requires_reason",
        ),
        CheckConstraint(
            "status <> 'merged' OR merged_into_detection_id IS NOT NULL",
            name="merged_requires_target",
        ),
        CheckConstraint(
            "merged_into_detection_id IS NULL OR merged_into_detection_id <> id",
            name="merge_not_self",
        ),
        CheckConstraint(
            "dismissal_reason IS NULL OR dismissal_reason IN ("
            "'false_positive', 'sensor_fault', 'planned_operation', "
            "'duplicate', 'insufficient_evidence', 'other')",
            name="dismissal_reason_allowed",
        ),
        Index("ix_anomaly_detections_status_detected_at", "status", "detected_at"),
        Index("ix_anomaly_detections_sensor_detected_at", "sensor_id", "detected_at"),
        Index("ix_anomaly_detections_priority_detected_at", "priority", "detected_at"),
        Index("ix_anomaly_detections_incident_id", "incident_id"),
        Index("ix_anomaly_detections_correlation_key", "correlation_key"),
    )

    detection_number: Mapped[str] = mapped_column(String(32), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sensor_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pipeline_segment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pipeline_segments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("detection_rules.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="new")
    trigger_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    reason_codes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reading_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    incident_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    data_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="simulated")
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissal_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    merged_into_detection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("anomaly_detections.id", ondelete="RESTRICT", name="fk_anomaly_detections_merged_into"),
        nullable=True,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="anomaly_detections")
    sensor: Mapped[Asset] = relationship(back_populates="anomaly_detections")
    pipeline_segment: Mapped[PipelineSegment | None] = relationship(back_populates="anomaly_detections")
    rule: Mapped[DetectionRule] = relationship(back_populates="detections")
    incident: Mapped[Incident | None] = relationship()
    evidence_items: Mapped[list[DetectionEvidence]] = relationship(
        back_populates="detection",
        cascade="all, delete-orphan",
    )
    investigation_events: Mapped[list[DetectionInvestigationEvent]] = relationship(
        back_populates="detection",
        cascade="all, delete-orphan",
        order_by="DetectionInvestigationEvent.created_at",
    )
    merged_into: Mapped[AnomalyDetection | None] = relationship(
        remote_side="AnomalyDetection.id",
        foreign_keys=[merged_into_detection_id],
    )


class DetectionEvidence(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "detection_evidence"
    __table_args__ = (
        Index("ix_detection_evidence_detection_id", "detection_id"),
        Index("ix_detection_evidence_metric", "metric"),
    )

    detection_id: Mapped[UUID] = mapped_column(
        ForeignKey("anomaly_detections.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    reading_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reading_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    detection: Mapped[AnomalyDetection] = relationship(back_populates="evidence_items")


class DetectionInvestigationEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only investigation history. Do not update or delete rows in application code."""

    __tablename__ = "detection_investigation_events"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_detection_investigation_events_public_id"),
        CheckConstraint(
            "event_type IN ('review_started', 'note_added', 'dismissed', "
            "'reopened', 'merged', 'promoted')",
            name="event_type_allowed",
        ),
        Index("ix_detection_investigation_events_detection_id", "detection_id"),
        Index(
            "ix_detection_investigation_events_detection_id_created_at",
            "detection_id",
            "created_at",
        ),
    )

    public_id: Mapped[str] = mapped_column(String(32), nullable=False)
    detection_id: Mapped[UUID] = mapped_column(
        ForeignKey("anomaly_detections.id", ondelete="CASCADE", name="fk_detection_investigation_events_detection_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    detection: Mapped[AnomalyDetection] = relationship(back_populates="investigation_events")
