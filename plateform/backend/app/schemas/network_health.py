from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.network.constants import MOCK_DATA_MODE

ReachabilityStatus = Literal["reachable", "unreachable", "unknown", "not_supported", "not_checked"]
SourceMode = Literal["seeded_demo", "nokia_simulator", "nokia_live"]


class NetworkEventSummary(BaseModel):
    id: str
    public_id: str
    event_id: str
    event_type: str
    status: str
    summary: str
    cluster_id: str | None
    device_id: str | None
    incident_id: str | None
    occurred_at: datetime
    data_mode: str = MOCK_DATA_MODE
    contract_version: str


class NetworkEventDetail(NetworkEventSummary):
    payload: dict[str, Any]
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    error_code: str | None
    error_message: str | None


class NetworkEventListResponse(BaseModel):
    items: list[NetworkEventSummary]
    total: int
    page: int
    page_size: int
    data_mode: str = MOCK_DATA_MODE
    note: str = "Historical Network Agent audit records — not current device health."


class LastTelemetry(BaseModel):
    observed_at: datetime | None = None
    pressure_kpa: float | None = None
    flow_lps: float | None = None
    temperature_c: float | None = None


class DeviceNetworkSnapshotSummary(BaseModel):
    snapshot_id: str
    asset_id: str
    asset_name: str
    asset_type: str
    zone_id: str | None
    zone_name: str | None
    location_label: str | None
    registered_latitude: float | None
    registered_longitude: float | None
    has_cellular_identity: bool
    device_msisdn_masked: str | None
    reachability_status: ReachabilityStatus
    reachable_via: str | None
    reachability_checked_at: datetime | None
    network_location_available: bool
    network_latitude: float | None
    network_longitude: float | None
    accuracy_radius_m: float | None
    location_area_type: str | None
    location_observed_at: datetime | None
    location_offset_m: float | None
    retrieved_at: datetime | None
    stale: bool
    provider: str | None
    source_mode: SourceMode | None
    data_source_label: str
    error_code: str | None = None
    error_message: str | None = None
    last_telemetry: LastTelemetry | None = None


class DeviceNetworkSnapshotDetail(DeviceNetworkSnapshotSummary):
    snapshot_public_id: str | None = None
    request_correlation_id: str | None = None
    cached: bool = False
    history: list["DeviceNetworkHistoryItem"] = Field(default_factory=list)


class DeviceNetworkHistoryItem(BaseModel):
    snapshot_id: str
    reachability_status: ReachabilityStatus
    reachable_via: str | None
    network_location_available: bool
    network_latitude: float | None
    network_longitude: float | None
    accuracy_radius_m: float | None
    retrieved_at: datetime
    source_mode: SourceMode
    error_code: str | None


class DeviceNetworkListResponse(BaseModel):
    items: list[DeviceNetworkSnapshotSummary]
    total: int
    source_mode: SourceMode
    data_source_label: str
    last_refresh_at: datetime | None


class DeviceNetworkSummary(BaseModel):
    cellular_devices: int
    reachable: int
    unreachable: int
    unknown_or_not_checked: int
    network_location_available: int
    stale_checks: int
    last_refresh_at: datetime | None
    source_mode: SourceMode
    data_source_label: str
    environment_label: str
    available_zones: list[str]
    note: str = "Device network observations from AquaPulse snapshots. Nokia reachability is not incident status."


class DeviceNetworkRefreshRequest(BaseModel):
    force: bool = False


class BulkDeviceNetworkRefreshRequest(BaseModel):
    force: bool = False
    asset_ids: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=50)


class BulkRefreshError(BaseModel):
    asset_id: str
    error_code: str
    error_message: str


class BulkDeviceNetworkRefreshResponse(BaseModel):
    requested: int
    succeeded: int
    failed: int
    skipped_cached: int
    items: list[DeviceNetworkSnapshotSummary]
    errors: list[BulkRefreshError]
    source_mode: SourceMode
    data_source_label: str
    partial_success: bool


class IncidentDeviceNetworkContext(BaseModel):
    incident_id: str
    asset_id: str | None
    available: bool
    reachability_status: ReachabilityStatus | None = None
    reachable_via: str | None = None
    reachability_checked_at: datetime | None = None
    network_location_available: bool = False
    network_latitude: float | None = None
    network_longitude: float | None = None
    accuracy_radius_m: float | None = None
    registered_latitude: float | None = None
    registered_longitude: float | None = None
    location_offset_m: float | None = None
    source_mode: SourceMode | None = None
    data_source_label: str | None = None
    device_msisdn_masked: str | None = None
    note: str = (
        "Nokia reachability is not incident status. "
        "Investigating, waiting for approval, and resolved remain incident workflow states."
    )


DeviceNetworkSnapshotDetail.model_rebuild()
