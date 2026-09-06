from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.assets import AssetType, OperationalStatus
from app.schemas.incidents import Classification, IncidentStatus, SeverityTier
from app.schemas.telemetry import FreshnessState


class MapFeatureType(str, Enum):
    asset = "asset"
    pipeline = "pipeline"
    incident = "incident"
    zone = "zone"


class GeoJSONGeometry(BaseModel):
    type: Literal["Point", "LineString", "MultiPolygon"]
    coordinates: Any


class ZoneFeatureProperties(BaseModel):
    code: str
    name: str
    country: str
    region: str
    asset_count: int = Field(ge=0)
    active_incident_count: int = Field(ge=0)


class PipelineFeatureProperties(BaseModel):
    external_id: str
    name: str
    status: str
    criticality: int
    zone: str
    population_served: int
    active_incident_count: int = Field(ge=0)
    connected_asset_count: int = Field(ge=0)


class AssetFeatureProperties(BaseModel):
    external_id: str
    name: str
    asset_type: AssetType
    operational_status: OperationalStatus
    health_score: float | None = None
    zone: str
    zone_id: str | None = None
    location_label: str | None = None
    has_cellular_identity: bool = False
    device_msisdn_masked: str | None = None
    pipeline_segment: str | None = None
    active_incident_count: int = Field(ge=0)
    last_seen_at: datetime | None = None
    latest_reading_at: datetime | None = None
    telemetry_freshness: FreshnessState | None = None
    latest_packet_loss_pct: float | None = None
    latest_signal_strength_dbm: int | None = None
    latest_battery_pct: float | None = None


class IncidentFeatureProperties(BaseModel):
    incident_number: str
    title: str
    severity: SeverityTier
    classification: Classification
    status: IncidentStatus
    detected_at: datetime
    related_asset_id: str | None = None
    related_segment_id: str | None = None
    summary: str | None = None


class DetectionFeatureProperties(BaseModel):
    detection_number: str
    priority: str
    status: str
    anomaly_score: float
    trigger_reason: str
    rule_code: str
    sensor_id: str
    zone: str
    detected_at: datetime
    data_mode: str = "simulated"


class MapFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: GeoJSONGeometry
    properties: (
        ZoneFeatureProperties
        | PipelineFeatureProperties
        | AssetFeatureProperties
        | IncidentFeatureProperties
        | DetectionFeatureProperties
    )


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[MapFeature]


class MapSummary(BaseModel):
    visible_zones: int = Field(ge=0)
    visible_pipelines: int = Field(ge=0)
    visible_assets: int = Field(ge=0)
    online: int = Field(ge=0)
    degraded: int = Field(ge=0)
    offline: int = Field(ge=0)
    active_incidents: int = Field(ge=0)
    critical_incidents: int = Field(ge=0)
    last_data_update: datetime | None = None
    data_mode: Literal["seeded_demo"] = "seeded_demo"


class NearbyItem(BaseModel):
    feature_type: Literal["asset", "pipeline", "incident"]
    id: str
    name: str
    distance_m: float = Field(ge=0)
    geometry: GeoJSONGeometry
    properties: AssetFeatureProperties | PipelineFeatureProperties | IncidentFeatureProperties


class NearbyResponse(BaseModel):
    origin: dict[str, float]
    radius_m: float
    items: list[NearbyItem]
    total: int = Field(ge=0)
