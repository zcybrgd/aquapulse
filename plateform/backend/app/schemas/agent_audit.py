from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

class AgentCount(BaseModel):
    key: str
    count: int


class AgentAuditEventSummary(BaseModel):
    id: str
    public_id: str
    agent_run_id: str | None
    agent_code: str
    contract_version: str
    pipeline_stage: str
    node_name: str | None
    sequence_number: int
    event_type: str
    status: str
    summary: str
    incident_public_id: str | None
    detection_public_id: str | None
    asset_public_id: str | None
    external_cluster_id: str | None
    external_device_id: str | None
    error_code: str | None
    error_message: str | None
    duration_ms: int | None
    data_mode: str = "ingested"
    occurred_at: datetime
    reasoning_summary: str | None


class AgentAuditEventDetail(AgentAuditEventSummary):
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    reasoning_trace: Any
    safety_checks: Any


class LinkedFinding(BaseModel):
    classification: str
    severity_tier: int
    confidence_score: float
    operator_justification: str | None
    mapping_status: str
    external_cluster_id: str | None
    mapped_detection_id: str | None


class AgentAuditRunSummary(BaseModel):
    id: str
    public_id: str
    agent_code: str
    agent_type: str
    contract_version: str
    pipeline_stages: list[str] = Field(default_factory=list)
    source_type: str
    source_public_id: str | None
    status: str
    classification: str | None
    investigation_severity: int | None
    decision: str | None
    duration_ms: int | None
    started_at: datetime
    related_incident: str | None
    related_detection: str | None
    related_device: str | None
    external_cluster_id: str | None
    data_mode: str
    blocked: bool
    contract_unconfirmed: bool
    mapping_status: str | None


class AgentAuditRunDetail(AgentAuditRunSummary):
    events: list[AgentAuditEventDetail]
    findings: list[LinkedFinding]
    recommendation_decisions: list[str]
    valve_command_sent: bool
    valve_command_confirmed: bool
    notification_sent: bool
    safety_status: str | None
    note: str


class AgentAuditRunListResponse(BaseModel):
    items: list[AgentAuditRunSummary]
    total: int
    page: int
    page_size: int
    data_mode: str = "ingested"
    reference_time: datetime


class AgentAuditEventListResponse(BaseModel):
    items: list[AgentAuditEventSummary]
    total: int
    page: int
    page_size: int
    data_mode: str = "ingested"
    reference_time: datetime


class AgentAuditSummary(BaseModel):
    total_runs: int
    successful_runs: int
    failed_runs: int
    blocked_actions: int
    average_duration_ms: float | None
    runs_by_agent: list[AgentCount]
    stages_reached: list[AgentCount]
    last_run_at: datetime | None
    unmapped_identity_count: int
    data_mode: str = "ingested"
    reference_time: datetime
    note: str = "Ingested agent result. Advisory only. Agent audit logs do not replace operator history."
