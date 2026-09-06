from fastapi import APIRouter, Depends, Query

from app.api.deps import get_analytics_service
from app.schemas.analytics import (
    AnalyticsAssetsResponse,
    AnalyticsDetectionsResponse,
    AnalyticsIncidentsResponse,
    AnalyticsOperationsResponse,
    AnalyticsOverviewResponse,
    AnalyticsTelemetryResponse,
    AnalyticsZonesResponse,
)
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    sensor: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsOverviewResponse:
    return service.overview(range, zone=zone, sensor=sensor)


@router.get("/telemetry", response_model=AnalyticsTelemetryResponse)
def get_analytics_telemetry(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    sensor: str | None = Query(default=None),
    interval: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsTelemetryResponse:
    return service.telemetry(range, zone=zone, sensor=sensor, interval=interval)


@router.get("/zones", response_model=AnalyticsZonesResponse)
def get_analytics_zones(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsZonesResponse:
    return service.zones(range, zone=zone)


@router.get("/detections", response_model=AnalyticsDetectionsResponse)
def get_analytics_detections(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    sensor: str | None = Query(default=None),
    interval: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsDetectionsResponse:
    return service.detections(range, zone=zone, sensor=sensor, interval=interval)


@router.get("/incidents", response_model=AnalyticsIncidentsResponse)
def get_analytics_incidents(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    sensor: str | None = Query(default=None),
    interval: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsIncidentsResponse:
    return service.incidents(range, zone=zone, sensor=sensor, interval=interval)


@router.get("/operations", response_model=AnalyticsOperationsResponse)
def get_analytics_operations(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    sensor: str | None = Query(default=None),
    interval: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsOperationsResponse:
    return service.operations(range, zone=zone, sensor=sensor, interval=interval)


@router.get("/assets", response_model=AnalyticsAssetsResponse)
def get_analytics_assets(
    range: str = Query(default="24h"),
    zone: str | None = Query(default=None),
    sensor: str | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsAssetsResponse:
    return service.assets(range, zone=zone, sensor=sensor)
