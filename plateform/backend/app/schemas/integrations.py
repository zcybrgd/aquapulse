from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SafetyFlags(BaseModel):
    camara_enabled: bool
    notifications_enabled: bool
    physical_commands_enabled: bool
    agent_execution_enabled: bool
    result_ingest_enabled: bool


class AgentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_code: str
    display_name: str
    enabled: bool
    mode: str
    contract_version: str
    url_configured: bool
    health_status: str
    last_health_check_at: datetime | None = None
    reachable: bool = False


class MappingCoverage(BaseModel):
    enabled_mappings: int
    unmapped_findings: int


class AgentRunSummary(BaseModel):
    run_id: str
    agent_type: str
    status: str
    source_type: str
    source_public_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    data_mode: str
    mapping_warning_count: int = 0
    error_code: str | None = None


class AgentReadiness(BaseModel):
    prepared: bool = True
    execution_enabled: bool = False
    banner: str = "Integration prepared — agent execution disabled"
    advisory_notice: str = "Agent result is advisory"
    actuation_notice: str = "No physical command can be executed"
    safety: SafetyFlags
    agents: list[AgentSummary]
    mapping_coverage: MappingCoverage
    last_runs: list[AgentRunSummary]
    contract_docs: dict[str, str]


class AgentIntegrationDetail(AgentSummary):
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContractMetadata(BaseModel):
    agent_code: str
    schema_version: str
    request_schema: str
    response_schema: str
    endpoints: list[str]
    notes: list[str]


class ValidationResult(BaseModel):
    valid: bool
    schema_version: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    side_effects: dict[str, bool]


class AgentRunDetail(AgentRunSummary):
    correlation_id: str
    idempotency_key: str
    contract_version: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any] | None = None
    validation_errors: list[Any] = Field(default_factory=list)
    mapping_warnings: list[Any] = Field(default_factory=list)
    error_message: str | None = None


class AgentFindingRecord(BaseModel):
    id: UUID
    run_id: str
    provider: str
    external_anomaly_id: str
    classification: str
    classification_label: str
    severity_tier: int
    severity_label: str
    confidence_score: float
    external_cluster_id: str | None = None
    external_segment_id: str | None = None
    external_valve_id: str | None = None
    mapped_detection_id: str | None = None
    mapped_sensor_id: str | None = None
    mapped_segment_id: str | None = None
    mapped_valve_id: str | None = None
    mapping_status: str
    review_status: str
    network_status: dict[str, Any]
    physical_deviations: dict[str, Any]
    criticality_metrics: dict[str, Any]
    operator_justification: str | None = None
    advisory: bool = True
    data_mode: str = "simulated"
    created_at: datetime


class AgentIngestAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"
    agent: str
    run_id: str
    created: int
    duplicates: int
    unmapped_ids: list[str] = Field(default_factory=list)


class AgentRecommendationRecord(BaseModel):
    id: UUID
    run_id: str
    provider: str
    external_result_id: str
    external_incident_id: str | None = None
    external_cluster_id: str | None = None
    external_device_id: str | None = None
    mapped_incident_number: str | None = None
    mapped_device_id: str | None = None
    incident_attached: bool
    severity_tier: int
    severity_label: str
    decision: str
    reachability: dict[str, Any]
    notification_sent: bool
    notification_verified: bool = False
    valve_command_sent: bool
    valve_command_confirmed: bool
    valve_command_verified: bool = False
    human_override_requested: bool
    human_override_response: str | None = None
    reasoning_trace: list[Any] | dict[str, Any]
    safety_status: str
    advisory: bool = True
    data_mode: str = "simulated"
    created_at: datetime


class CompatReachability(BaseModel):
    device_id: str
    reachable: bool
    checked_at: datetime
    raw_signal_quality: int | None = None
    mapping_status: str
    aquapulse_asset_id: str | None = None
    data_mode: str = "mock"


class CompatQodResponse(BaseModel):
    device_id: str
    reserved: bool = False
    denied: bool = True
    reason: str
    data_mode: str = "mock"
    real_network_guarantee: bool = False


class CompatNotifyResponse(BaseModel):
    sent: bool = False
    reason: str
    data_mode: str = "mock"


class CompatValveIsolateResponse(BaseModel):
    confirmed: bool = False
    executed: bool = False
    status: str = "blocked"
    reason: str
    data_mode: str = "mock"


class CompatValveStatusResponse(BaseModel):
    device_id: str
    aquapulse_valve_id: str | None = None
    current_position: str | None = None
    mapping_status: str
    data_mode: str = "mock"
