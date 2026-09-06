from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.incidents import Classification, IncidentStatus, SeverityTier, SortOrder


class AssetType(str, Enum):
    sensor = "sensor"
    valve = "valve"
    gateway = "gateway"


class OperationalStatus(str, Enum):
    online = "online"
    degraded = "degraded"
    offline = "offline"


class ValvePosition(str, Enum):
    open = "open"
    closed = "closed"
    partial = "partial"
    unknown = "unknown"


class ControlMode(str, Enum):
    manual = "manual"
    remote = "remote"
    automatic = "automatic"


class MaintenanceFilter(str, Enum):
    due = "due"
    upcoming = "upcoming"
    scheduled = "scheduled"


class AssetSortField(str, Enum):
    name = "name"
    asset_type = "asset_type"
    status = "status"
    health_score = "health_score"
    last_seen = "last_seen"
    next_maintenance = "next_maintenance"


class MeasurementRange(BaseModel):
    quantity: str
    minimum: float
    maximum: float
    unit: str


class SensorAttributes(BaseModel):
    measurement_types: list[str] = Field(default_factory=list)
    sampling_interval_seconds: int | None = None
    battery_pct: float | None = None
    signal_strength_dbm: int | None = None
    calibration_date: datetime | None = None
    measurement_ranges: list[MeasurementRange] = Field(default_factory=list)
    supported_units: list[str] = Field(default_factory=list)


class ValveAttributes(BaseModel):
    current_position: ValvePosition | None = None
    control_mode: ControlMode | None = None
    failsafe_position: str | None = None
    actuation_type: str | None = None
    last_command_at: datetime | None = None


class GatewayAttributes(BaseModel):
    provider: str | None = None
    connection_type: str | None = None
    protocols: list[str] = Field(default_factory=list)
    signal_strength_dbm: int | None = None
    packet_delivery_status: str | None = None


class DeviceLocation(BaseModel):
    zone_id: str
    zone_name: str
    location_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class RelatedIncidentSummary(BaseModel):
    id: str
    incident_number: str
    title: str
    classification: Classification
    severity: SeverityTier
    status: IncidentStatus
    detected_at: datetime


class AssetSummary(BaseModel):
    id: str
    external_id: str
    name: str
    asset_type: AssetType
    operational_status: OperationalStatus
    health_score: float | None = None
    zone: str
    zone_id: str
    zone_name: str
    location_label: str | None = None
    has_cellular_identity: bool = False
    device_msisdn_masked: str | None = None
    pipeline_segment: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    battery_pct: float | None = None
    current_position: ValvePosition | None = None
    last_seen_at: datetime | None = None
    next_maintenance_at: datetime | None = None
    maintenance_state: str


class AssetDetail(AssetSummary):
    serial_number: str | None = None
    firmware_version: str | None = None
    installed_at: datetime | None = None
    commissioned_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    device_location: DeviceLocation
    last_maintenance_at: datetime | None = None
    control_mode: ControlMode | None = None
    signal_strength_dbm: int | None = None
    sampling_interval_seconds: int | None = None
    sensor: SensorAttributes | None = None
    valve: ValveAttributes | None = None
    gateway: GatewayAttributes | None = None
    related_incidents: list[RelatedIncidentSummary] = Field(default_factory=list)


class AssetListSummary(BaseModel):
    total_assets: int = Field(ge=0)
    online: int = Field(ge=0)
    degraded: int = Field(ge=0)
    offline: int = Field(ge=0)
    maintenance_due: int = Field(ge=0)


class AssetListResponse(BaseModel):
    items: list[AssetSummary]
    total: int = Field(ge=0)
    summary: AssetListSummary


class AssetIncidentListResponse(BaseModel):
    asset_id: str
    items: list[RelatedIncidentSummary]
    total: int = Field(ge=0)


class AssetHealthPoint(BaseModel):
    timestamp: datetime
    health_score: float
    battery_pct: float | None = None
    signal_strength_dbm: int | None = None
    availability_pct: float | None = None
    position_confirmed: bool | None = None
    packet_delivery_pct: float | None = None
    pressure_kpa: float | None = None
    flow_lps: float | None = None
    packet_loss_pct: float | None = None
    temperature_c: float | None = None


class AssetHealthResponse(BaseModel):
    asset_id: str
    series_kind: str = "mock_recent_health"
    note: str
    items: list[AssetHealthPoint]
    range: str | None = None
    freshness: str | None = None
    last_reading_at: datetime | None = None
    data_mode: str | None = None
