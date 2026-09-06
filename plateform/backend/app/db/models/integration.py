from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class AgentIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_integrations"
    __table_args__ = (
        UniqueConstraint("agent_code", name="uq_agent_integrations_agent_code"),
        CheckConstraint("mode IN ('disabled', 'mock', 'remote')", name="agent_mode_allowed"),
        CheckConstraint(
            "health_status IN ('unknown', 'disabled', 'healthy', 'unhealthy', 'unreachable')",
            name="agent_health_allowed",
        ),
    )

    agent_code: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    health_status: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    runs: Mapped[list[AgentRun]] = relationship(back_populates="integration")


class AgentRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_agent_runs_public_id"),
        Index("ix_agent_runs_idempotency_key", "idempotency_key"),
        Index("ix_agent_runs_correlation_id", "correlation_id"),
        CheckConstraint(
            "status IN ('pending', 'validating', 'ready', 'running', 'succeeded', 'failed', 'rejected', 'cancelled')",
            name="agent_run_status_allowed",
        ),
        CheckConstraint(
            "agent_type IN ('investigation_agent', 'response_agent', 'network_management_agent')",
            name="agent_run_type_allowed",
        ),
    )

    public_id: Mapped[str] = mapped_column(String(32), nullable=False)
    agent_integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_integrations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    correlation_id: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_public_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_errors: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    mapping_warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="simulated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    integration: Mapped[AgentIntegration] = relationship(back_populates="runs")
    findings: Mapped[list[AgentFinding]] = relationship(back_populates="run")
    recommendations: Mapped[list[AgentResponseRecommendation]] = relationship(back_populates="run")


class AgentFinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_findings"
    __table_args__ = (
        UniqueConstraint("provider", "external_anomaly_id", name="uq_agent_findings_provider_anomaly"),
        CheckConstraint(
            "classification IN ('confirmed_anomaly', 'confirmed_instrument_fault')",
            name="finding_classification_allowed",
        ),
        CheckConstraint("severity_tier BETWEEN 1 AND 3", name="finding_severity_range"),
        CheckConstraint(
            "mapping_status IN ('mapped', 'unmapped', 'partial')",
            name="finding_mapping_status_allowed",
        ),
        CheckConstraint(
            "review_status IN ('unread', 'reviewed', 'dismissed')",
            name="finding_review_status_allowed",
        ),
        Index("ix_agent_findings_agent_run_id", "agent_run_id"),
    )

    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="investigation_agent")
    external_anomaly_id: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    classification: Mapped[str] = mapped_column(String(60), nullable=False)
    severity_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    external_cluster_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_segment_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_valve_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    anomaly_detection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("anomaly_detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mapped_detection_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mapped_sensor_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mapped_segment_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mapped_valve_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    network_status: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    physical_deviations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    criticality_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    operator_justification: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    mapping_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmapped")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unread")
    raw_finding: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    run: Mapped[AgentRun] = relationship(back_populates="findings")
    anomaly_detection = relationship("AnomalyDetection")


class AgentResponseRecommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_response_recommendations"
    __table_args__ = (
        UniqueConstraint("provider", "external_result_id", name="uq_agent_recs_provider_result"),
        CheckConstraint(
            "decision IN ('LOG_ONLY', 'ALERT_AND_AWAIT', 'AUTONOMOUS_ISOLATE', 'ESCALATE_UNREACHABLE')",
            name="recommendation_decision_allowed",
        ),
        CheckConstraint("severity_tier BETWEEN 1 AND 3", name="recommendation_severity_range"),
        CheckConstraint(
            "safety_status IN ('advisory', 'blocked', 'agent_reported_unverified')",
            name="recommendation_safety_allowed",
        ),
        Index("ix_agent_recs_agent_run_id", "agent_run_id"),
    )

    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="response_agent")
    external_result_id: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_incident_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_cluster_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mapped_incident_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mapped_device_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reachability: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notification_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valve_command_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valve_command_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    human_override_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    human_override_response: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reasoning_trace: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    safety_status: Mapped[str] = mapped_column(String(40), nullable=False, default="advisory")
    raw_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    run: Mapped[AgentRun] = relationship(back_populates="recommendations")


class IntegrationIdentityMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_identity_mappings"
    __table_args__ = (
        UniqueConstraint("provider", "entity_type", "external_id", name="uq_identity_mapping_provider_type_ext"),
        CheckConstraint(
            "entity_type IN ('sensor_cluster', 'sensor', 'segment', 'valve', 'device', 'incident', 'detection')",
            name="identity_entity_type_allowed",
        ),
        CheckConstraint(
            "internal_entity_type IN ('sensor_cluster', 'sensor', 'segment', 'valve', 'device', 'incident', 'detection')",
            name="identity_internal_type_allowed",
        ),
        Index("ix_identity_mappings_internal", "internal_entity_type", "internal_public_id"),
    )

    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    internal_entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    internal_public_id: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
