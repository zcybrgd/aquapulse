from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.incidents import Classification, IncidentSummary, SeverityTier


class DetectionStatus(str, Enum):
    new = "new"
    queued = "queued"
    under_review = "under_review"
    dismissed = "dismissed"
    promoted = "promoted"
    merged = "merged"


class DetectionPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DetectionSortField(str, Enum):
    detected_at = "detected_at"
    priority = "priority"
    score = "score"
    status = "status"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class DetectionEvidenceItem(BaseModel):
    metric: str
    observed_value: float
    baseline_value: float | None = None
    threshold_value: float | None = None
    unit: str
    evidence_type: str
    reading_start_time: datetime
    reading_end_time: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class DetectionSummary(BaseModel):
    id: str
    detection_number: str
    status: DetectionStatus
    priority: DetectionPriority
    anomaly_score: float = Field(ge=0, le=1)
    trigger_reason: str
    reason_codes: list[str]
    rule_code: str
    rule_name: str
    rule_version: int
    sensor_id: str
    sensor_name: str
    zone: str
    pipeline_segment: str | None = None
    detected_at: datetime
    window_start: datetime
    window_end: datetime
    data_mode: str
    incident_id: str | None = None
    reviewed_by: str | None = None
    review_started_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismissal_reason: str | None = None
    merged_into_detection_id: str | None = None
    resolved_at: datetime | None = None
    updated_at: datetime | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    screening_priority_label: str = "Screening priority"
    awaiting_agent_investigation: bool = False
    has_agent_finding: bool = False


class DetectionListResponse(BaseModel):
    items: list[DetectionSummary]
    total: int = Field(ge=0)
    data_mode: str = "simulated"


class DetectionDetail(BaseModel):
    id: str
    detection_number: str
    status: DetectionStatus
    priority: DetectionPriority
    anomaly_score: float = Field(ge=0, le=1)
    trigger_reason: str
    reason_codes: list[str]
    rule_code: str
    rule_name: str
    rule_version: int
    sensor_id: str
    sensor_name: str
    asset_status: str
    zone: str
    pipeline_segment: str | None = None
    pipeline_segment_id: str | None = None
    criticality: int | None = None
    population_served: int | None = None
    detected_at: datetime
    window_start: datetime
    window_end: datetime
    reading_count: int
    correlation_key: str
    score_explanation: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    evidence: list[DetectionEvidenceItem] = Field(default_factory=list)
    related_detections: list[DetectionSummary] = Field(default_factory=list)
    incident_id: str | None = None
    telemetry_freshness: str | None = None
    latest_reading_at: datetime | None = None
    data_mode: str = "simulated"
    reviewed_by: str | None = None
    review_started_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismissal_reason: str | None = None
    merged_into_detection_id: str | None = None
    resolved_at: datetime | None = None
    updated_at: datetime | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    screening_priority_label: str = "Screening priority"
    awaiting_agent_investigation: bool = False
    has_agent_finding: bool = False
    agent_finding: dict[str, Any] | None = None


class DetectionEvidenceResponse(BaseModel):
    detection_id: str
    items: list[DetectionEvidenceItem]
    data_mode: str = "simulated"


class DetectionQueueStats(BaseModel):
    new: int = Field(ge=0)
    queued: int = Field(ge=0)
    under_review: int = Field(ge=0)
    high_priority: int = Field(ge=0)
    critical_priority: int = Field(ge=0)
    total: int = Field(ge=0)
    last_run_at: datetime | None = None
    last_run_deduplicated: int | None = None
    highest_priority: DetectionSummary | None = None
    data_mode: str = "simulated"


class TelemetryWindow(BaseModel):
    start: datetime
    end: datetime


class AgentSensorIdentity(BaseModel):
    id: str
    name: str
    operational_status: str
    manufacturer: str | None = None
    model: str | None = None


class AgentNetworkMetadata(BaseModel):
    zone: str
    signal_strength_dbm: int | None = None
    packet_loss_pct: float | None = None
    telemetry_freshness: str | None = None
    latest_reading_at: datetime | None = None


class AgentRuleTrigger(BaseModel):
    rule_code: str
    rule_name: str
    rule_version: int
    reason_codes: list[str]
    trigger_reason: str
    threshold: float | None = None
    secondary_threshold: float | None = None


class AgentPipelineContext(BaseModel):
    segment_id: str | None = None
    segment_name: str | None = None
    criticality: int | None = None
    population_served: int | None = None


class InvestigationAgentInputV1(BaseModel):
    """Future Investigation Agent input. No agent is invoked when this is built."""

    schema_version: Literal["1"] = "1"
    detection_id: str
    detected_at: datetime
    telemetry_window: TelemetryWindow
    recent_readings_reference: dict[str, Any]
    sensor: AgentSensorIdentity
    network_metadata: AgentNetworkMetadata
    rule_triggers: list[AgentRuleTrigger]
    structured_evidence: list[DetectionEvidenceItem]
    pipeline_context: AgentPipelineContext
    criticality: int | None = None
    population_served: int | None = None
    current_asset_status: str
    data_mode: str = "simulated"
    agent_executed: Literal[False] = False
    note: str = (
        "No investigation agent has run. This payload is the versioned input contract "
        "for a future agent that will classify leak, connectivity, sensor fault, or normal."
    )


class DismissalReason(str, Enum):
    false_positive = "false_positive"
    sensor_fault = "sensor_fault"
    planned_operation = "planned_operation"
    duplicate = "duplicate"
    insufficient_evidence = "insufficient_evidence"
    other = "other"


class InvestigationEventType(str, Enum):
    review_started = "review_started"
    note_added = "note_added"
    dismissed = "dismissed"
    reopened = "reopened"
    merged = "merged"
    promoted = "promoted"


def _trim_actor(value: str) -> str:
    """Temporary development identity. Not trusted authentication."""
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("actor_name is required")
    return trimmed


class ActorRequest(BaseModel):
    """Temporary development identity. Not trusted authentication. Not a user session."""

    actor_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Temporary development identity. Not trusted authentication.",
    )

    @field_validator("actor_name")
    @classmethod
    def validate_actor_name(cls, value: str) -> str:
        return _trim_actor(value)


class StartReviewRequest(ActorRequest):
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class AddNoteRequest(ActorRequest):
    note: str = Field(..., min_length=1, max_length=2000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("note is required")
        return trimmed


class DismissDetectionRequest(ActorRequest):
    reason_code: DismissalReason
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ReopenDetectionRequest(ActorRequest):
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class MergeDetectionRequest(ActorRequest):
    target_detection_id: str = Field(..., min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("target_detection_id")
    @classmethod
    def validate_target(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("target_detection_id is required")
        return trimmed.upper()

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class PromoteDetectionRequest(ActorRequest):
    title: str = Field(..., min_length=1, max_length=300)
    severity: SeverityTier
    classification: Classification
    summary: str = Field(..., min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "summary")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("this field is required")
        return trimmed

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class InvestigationEventItem(BaseModel):
    id: str
    event_type: InvestigationEventType
    from_status: DetectionStatus | None = None
    to_status: DetectionStatus | None = None
    actor_name: str
    note: str | None = None
    reason_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    target_detection_id: str | None = None
    incident_id: str | None = None


class InvestigationHistoryResponse(BaseModel):
    detection_id: str
    events: list[InvestigationEventItem]


class PromoteDetectionResponse(BaseModel):
    detection: DetectionDetail
    incident: IncidentSummary
