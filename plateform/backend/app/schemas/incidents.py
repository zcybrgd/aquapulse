from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SeverityTier(str, Enum):
    tier_1 = "tier_1"
    tier_2 = "tier_2"
    tier_3 = "tier_3"


class Classification(str, Enum):
    confirmed_leak = "confirmed_leak"
    suspected_leak = "suspected_leak"
    connectivity_degradation = "connectivity_degradation"
    sensor_fault = "sensor_fault"
    pressure_anomaly = "pressure_anomaly"
    normal_demand_spike = "normal_demand_spike"
    insufficient_data = "insufficient_data"


class IncidentStatus(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    investigating = "investigating"
    awaiting_approval = "awaiting_approval"
    responding = "responding"
    monitoring = "monitoring"
    resolved = "resolved"
    false_alarm = "false_alarm"


class ResolutionCode(str, Enum):
    leak_repaired = "leak_repaired"
    isolated_for_maintenance = "isolated_for_maintenance"
    sensor_fault = "sensor_fault"
    planned_operation = "planned_operation"
    false_alarm = "false_alarm"
    monitoring_completed = "monitoring_completed"
    other = "other"


class ResponseTaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ResponseTaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TimelineSource(str, Enum):
    detector = "detector"
    agent = "agent"
    network = "network"
    operator = "operator"
    system = "system"


class SortField(str, Enum):
    detected_at = "detected_at"
    severity = "severity"
    status = "status"
    estimated_loss = "estimated_loss"
    priority = "priority"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class IncidentError(BaseModel):
    message: str
    code: str = "incident_not_found"


class EvidenceItem(BaseModel):
    id: str
    kind: str
    title: str
    detail: str


class IncidentTelemetryPoint(BaseModel):
    timestamp: datetime
    pressure: float
    flow_rate: float
    packet_loss: float = Field(ge=0, le=100)
    is_detection: bool = False


class IncidentSummary(BaseModel):
    id: str
    incident_number: str
    title: str
    classification: Classification
    severity: SeverityTier
    status: IncidentStatus
    zone: str
    pipeline_segment: str
    location: str
    detected_at: datetime
    updated_at: datetime
    estimated_water_loss_m3: float
    assigned_operator: str | None = None


class IncidentDetail(IncidentSummary):
    confidence: float = Field(ge=0, le=100)
    sensor: str
    associated_valve: str
    latitude: float
    longitude: float
    population_affected: int = Field(ge=0)
    current_summary: str
    pressure_change_bar: float
    flow_change_m3h: float
    network_condition: str
    signal_strength_dbm: int
    packet_loss_percent: float = Field(ge=0, le=100)
    device_reachability: str
    network_priority_status: str
    agent_investigation_summary: str
    recommended_action: str
    evidence: list[EvidenceItem]
    telemetry: list[IncidentTelemetryPoint]


class IncidentListResponse(BaseModel):
    items: list[IncidentSummary]
    total: int = Field(ge=0)


class TimelineEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    source: TimelineSource
    status: str
    actor_name: str | None = None
    response_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    incident_id: str
    events: list[TimelineEvent]


def _trim_actor(value: str) -> str:
    """Temporary development identity. Not trusted authentication."""
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("actor_name is required")
    return trimmed


def _trim_optional(value: str | None, *, maximum: int = 2000) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    return trimmed[:maximum]


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


class NoteRequest(ActorRequest):
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class AcknowledgeRequest(NoteRequest):
    pass


class AssignIncidentRequest(NoteRequest):
    assigned_to: str = Field(..., min_length=1, max_length=120)

    @field_validator("assigned_to")
    @classmethod
    def validate_assignee(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("assigned_to is required")
        return trimmed


class ResolveIncidentRequest(ActorRequest):
    resolution_code: ResolutionCode
    resolution_summary: str = Field(..., min_length=1, max_length=2000)
    confirm_incomplete_tasks: bool = False

    @field_validator("resolution_summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("resolution_summary is required")
        return trimmed


class FalseAlarmRequest(ActorRequest):
    resolution_summary: str = Field(..., min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("resolution_summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("resolution_summary is required")
        return trimmed

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class ReopenIncidentRequest(NoteRequest):
    pass


class CreateResponseTaskRequest(ActorRequest):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: ResponseTaskPriority = ResponseTaskPriority.medium
    assigned_to: str | None = Field(default=None, max_length=120)
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title is required")
        return trimmed

    @field_validator("description", "assigned_to")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=2000)


class UpdateResponseTaskRequest(ActorRequest):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: ResponseTaskPriority | None = None
    assigned_to: str | None = Field(default=None, max_length=120)
    due_at: datetime | None = None

    @field_validator("title", "description", "assigned_to")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=2000)


class CompleteResponseTaskRequest(ActorRequest):
    completion_note: str | None = Field(default=None, max_length=2000)

    @field_validator("completion_note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class ResponseTaskItem(BaseModel):
    id: str
    public_id: str
    incident_id: str
    title: str
    description: str | None = None
    status: ResponseTaskStatus
    priority: ResponseTaskPriority
    assigned_to: str | None = None
    created_by: str
    due_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None
    completion_note: str | None = None
    created_at: datetime
    updated_at: datetime
    overdue: bool = False


class ResponseTaskListResponse(BaseModel):
    incident_id: str
    items: list[ResponseTaskItem]
    total: int = Field(ge=0)
    incomplete: int = Field(ge=0)


class IncidentOperationsResponse(BaseModel):
    incident_id: str
    status: IncidentStatus
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    assigned_to: str | None = None
    response_started_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_code: ResolutionCode | None = None
    resolution_summary: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    incomplete_task_count: int = Field(ge=0, default=0)
    tasks: list[ResponseTaskItem] = Field(default_factory=list)


class OperationsSummary(BaseModel):
    active_incidents: int = Field(ge=0)
    unacknowledged: int = Field(ge=0)
    acknowledged: int = Field(ge=0)
    investigating: int = Field(ge=0)
    awaiting_approval: int = Field(ge=0)
    responding: int = Field(ge=0)
    overdue_tasks: int = Field(ge=0)
    critical_active: int = Field(ge=0)


class OperationsQueueItem(IncidentSummary):
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    assigned_to: str | None = None
    response_started_at: datetime | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    open_task_count: int = Field(ge=0, default=0)
    overdue_task_count: int = Field(ge=0, default=0)
    completed_task_count: int = Field(ge=0, default=0)
    latest_update: str | None = None
    latest_update_at: datetime | None = None


class OperationsQueueResponse(BaseModel):
    items: list[OperationsQueueItem]
    total: int = Field(ge=0)
    summary: OperationsSummary
    overdue_tasks: list[ResponseTaskItem] = Field(default_factory=list)
    upcoming_tasks: list[ResponseTaskItem] = Field(default_factory=list)
    data_mode: Literal["simulated"] = "simulated"
