from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str = Field(examples=["AquaPulse API"])
    environment: str = Field(examples=["development"])
    database: str = Field(examples=["connected", "unavailable"])
    postgis: str = Field(examples=["available", "unavailable"])
    timescaledb: str = Field(examples=["available", "unavailable"])


class DatabaseHealthResponse(BaseModel):
    status: str = Field(examples=["ok", "unavailable"])
    database: str = Field(examples=["connected", "unavailable"])
    postgis: str = Field(examples=["available", "unavailable"])
    timescaledb: str = Field(examples=["available", "unavailable"])
    detail: dict[str, str] | None = None


class DashboardSummary(BaseModel):
    active_incidents: int = Field(ge=0)
    critical_incidents: int = Field(ge=0)
    online_sensors: int = Field(ge=0)
    total_sensors: int = Field(ge=0)
    network_health_percent: float = Field(ge=0, le=100)
    estimated_water_loss_m3: float = Field(ge=0)
    average_response_time_min: float = Field(ge=0)
    awaiting_approval: int = Field(ge=0, default=0)
    responding: int = Field(ge=0, default=0)
    overdue_response_tasks: int = Field(ge=0, default=0)


class TelemetryReading(BaseModel):
    timestamp: datetime
    pressure: float = Field(description="Network pressure in bar")
    flow_rate: float = Field(description="Flow rate in m³/h")
    packet_loss: float = Field(ge=0, le=100, description="Packet loss percentage")


class TelemetryResponse(BaseModel):
    readings: list[TelemetryReading]
    range: str = "1h"
    data_mode: str = "simulated"
    last_updated: datetime | None = None
    network_health_percent: float | None = None
