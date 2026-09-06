from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.analytics_constants import MetricInterpretation, TrendDirection


class AnalyticsFilters(BaseModel):
    zone: str | None = None
    sensor: str | None = None
    interval: str | None = None


class AnalyticsEnvelope(BaseModel):
    range: str
    start: datetime
    end: datetime
    generated_at: datetime
    data_mode: Literal["simulated"] = "simulated"
    filters: AnalyticsFilters


class ComparedMetric(BaseModel):
    key: str
    label: str
    unit: str | None = None
    current: float | None = None
    previous: float | None = None
    change: float | None = None
    change_pct: float | None = None
    trend: TrendDirection
    interpretation: MetricInterpretation = "neutral"


class NamedCount(BaseModel):
    key: str
    label: str
    count: int = Field(ge=0)


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    pressure_bar: float | None = None
    flow_m3h: float | None = None
    packet_loss_pct: float | None = None
    completeness_pct: float | None = None
    reporting_sensors: int | None = None
    reading_count: int | None = None
    detections: int | None = None
    incidents: int | None = None
    mean_response_minutes: float | None = None


class AnalyticsOverviewResponse(AnalyticsEnvelope):
    kpis: list[ComparedMetric]
    telemetry: dict[str, ComparedMetric]
    events: dict[str, ComparedMetric]
    operations: dict[str, ComparedMetric]
    available_zones: list[str]
    available_sensors: list[str]


class AnalyticsTelemetryResponse(AnalyticsEnvelope):
    interval: str
    summary: dict[str, ComparedMetric]
    series: list[TimeSeriesPoint]
    reporting_sensors: int
    stale_sensors: int
    offline_sensors: int
    selected_sensors: int


class ZoneAnalyticsRow(BaseModel):
    zone: str
    reporting_sensors: int
    selected_sensors: int
    telemetry_completeness_pct: float | None = None
    average_pressure_bar: float | None = None
    average_flow_m3h: float | None = None
    detection_count: int
    active_incident_count: int
    average_asset_health: float | None = None
    overdue_response_tasks: int
    sufficient_data: bool


class AnalyticsZonesResponse(AnalyticsEnvelope):
    items: list[ZoneAnalyticsRow]


class AnalyticsDetectionsResponse(AnalyticsEnvelope):
    interval: str
    created: ComparedMetric
    dismissed: ComparedMetric
    promoted: ComparedMetric
    promotion_rate: ComparedMetric
    by_priority: list[NamedCount]
    by_rule: list[NamedCount]
    series: list[TimeSeriesPoint]


class AnalyticsIncidentsResponse(AnalyticsEnvelope):
    interval: str
    created: ComparedMetric
    resolved: ComparedMetric
    false_alarms: ComparedMetric
    by_severity: list[NamedCount]
    by_classification: list[NamedCount]
    by_status: list[NamedCount]
    series: list[TimeSeriesPoint]


class AnalyticsOperationsResponse(AnalyticsEnvelope):
    interval: str
    mean_acknowledgement_minutes: ComparedMetric
    median_acknowledgement_minutes: ComparedMetric
    mean_response_start_minutes: ComparedMetric
    mean_resolution_minutes: ComparedMetric
    open_response_tasks: ComparedMetric
    completed_response_tasks: ComparedMetric
    overdue_response_tasks: ComparedMetric
    series: list[TimeSeriesPoint]


class AssetHealthBucket(BaseModel):
    key: str
    label: str
    count: int = Field(ge=0)


class AnalyticsAssetsResponse(AnalyticsEnvelope):
    health_bands: list[AssetHealthBucket]
    operational_status: list[NamedCount]
    connectivity: list[NamedCount]
    average_health: float | None = None
    sensor_count: int
    total_assets: int
