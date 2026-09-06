from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TelemetryMetric(str, Enum):
    pressure = "pressure"
    flow = "flow"
    temperature = "temperature"
    signal = "signal"
    packet_loss = "packet_loss"
    battery = "battery"


class TelemetryRange(str, Enum):
    one_hour = "1h"
    six_hours = "6h"
    twenty_four_hours = "24h"
    seven_days = "7d"


class TelemetryInterval(str, Enum):
    raw = "raw"
    one_minute = "1m"
    five_minutes = "5m"
    fifteen_minutes = "15m"
    one_hour = "1h"


class FreshnessState(str, Enum):
    fresh = "fresh"
    stale = "stale"
    offline = "offline"


class MetricUnit(BaseModel):
    metric: str
    unit: str
    display_unit: str


class TelemetrySample(BaseModel):
    time: datetime
    pressure_kpa: float | None = None
    flow_lps: float | None = None
    temperature_c: float | None = None
    signal_strength_dbm: int | None = None
    packet_loss_pct: float | None = None
    battery_pct: float | None = None


class SensorTelemetryHistory(BaseModel):
    sensor_id: str
    name: str
    range: str
    start: datetime
    end: datetime
    interval: str
    metrics: list[str]
    units: list[MetricUnit]
    data_mode: Literal["simulated"] = "simulated"
    items: list[TelemetrySample]
    total: int = Field(ge=0)


class LatestTelemetry(BaseModel):
    sensor_id: str
    name: str
    time: datetime | None = None
    pressure_kpa: float | None = None
    flow_lps: float | None = None
    temperature_c: float | None = None
    signal_strength_dbm: int | None = None
    packet_loss_pct: float | None = None
    battery_pct: float | None = None
    freshness: FreshnessState
    age_seconds: int | None = None
    data_mode: Literal["simulated"] = "simulated"


class NetworkTelemetrySummary(BaseModel):
    sensor_count: int = Field(ge=0)
    fresh_sensors: int = Field(ge=0)
    stale_sensors: int = Field(ge=0)
    offline_sensors: int = Field(ge=0)
    average_packet_delivery_pct: float | None = None
    average_signal_strength_dbm: float | None = None
    average_battery_pct: float | None = None
    last_telemetry_at: datetime | None = None
    data_mode: Literal["simulated"] = "simulated"


class LatestTelemetryBatch(BaseModel):
    items: list[LatestTelemetry]
    total: int = Field(ge=0)
    data_mode: Literal["simulated"] = "simulated"
    last_telemetry_at: datetime | None = None


class IngestReading(BaseModel):
    sensor_external_id: str
    time: datetime
    source_message_id: str
    pressure_kpa: float | None = None
    flow_lps: float | None = None
    temperature_c: float | None = None
    signal_strength_dbm: int | None = None
    packet_loss_pct: float | None = None
    battery_pct: float | None = None
    quality_flags: int = 0
    received_at: datetime | None = None
    raw_payload: dict | None = None


class IngestResult(BaseModel):
    status: Literal["inserted", "duplicate"]
    sensor_id: str
    time: datetime
    source_message_id: str
