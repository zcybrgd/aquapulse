from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_telemetry_service
from app.schemas.telemetry import (
    LatestTelemetry,
    LatestTelemetryBatch,
    NetworkTelemetrySummary,
    SensorTelemetryHistory,
    TelemetryInterval,
    TelemetryMetric,
    TelemetryRange,
)
from app.services.telemetry import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/sensors/latest", response_model=LatestTelemetryBatch)
def get_latest_batch(
    service: TelemetryService = Depends(get_telemetry_service),
) -> LatestTelemetryBatch:
    return service.latest_batch()


@router.get("/sensors/{sensor_id}", response_model=SensorTelemetryHistory)
def get_sensor_history(
    sensor_id: str,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    range: TelemetryRange | None = Query(default=None),
    interval: TelemetryInterval = Query(default=TelemetryInterval.raw),
    metrics: str | None = Query(default=None, description="Comma-separated metric names"),
    limit: int | None = Query(default=None, ge=1, le=2000),
    service: TelemetryService = Depends(get_telemetry_service),
) -> SensorTelemetryHistory:
    metric_list = [item.strip() for item in metrics.split(",") if item.strip()] if metrics else None
    return service.history(
        sensor_id,
        start=start,
        end=end,
        range_key=range.value if range else None,
        interval=interval.value,
        metrics=metric_list,
        limit=limit,
    )


@router.get("/sensors/{sensor_id}/latest", response_model=LatestTelemetry)
def get_sensor_latest(
    sensor_id: str,
    service: TelemetryService = Depends(get_telemetry_service),
) -> LatestTelemetry:
    return service.latest(sensor_id)


@router.get("/network/summary", response_model=NetworkTelemetrySummary)
def get_network_summary(
    service: TelemetryService = Depends(get_telemetry_service),
) -> NetworkTelemetrySummary:
    return service.network_summary()
