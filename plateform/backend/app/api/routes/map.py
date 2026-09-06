from fastapi import APIRouter, Depends, Query

from app.api.deps import get_map_service
from app.schemas.assets import AssetType, OperationalStatus
from app.schemas.incidents import IncidentStatus, SeverityTier
from app.schemas.map import FeatureCollection, MapSummary, NearbyResponse
from app.services.map import MapService

router = APIRouter(prefix="/map", tags=["map"])

MAX_RADIUS_M = 25_000


@router.get("/zones", response_model=FeatureCollection)
def get_map_zones(
    zone: str | None = Query(default=None),
    service: MapService = Depends(get_map_service),
) -> FeatureCollection:
    return service.zones(zone=zone)


@router.get("/pipelines", response_model=FeatureCollection)
def get_map_pipelines(
    zone: str | None = Query(default=None),
    service: MapService = Depends(get_map_service),
) -> FeatureCollection:
    return service.pipelines(zone=zone)


@router.get("/assets", response_model=FeatureCollection)
def get_map_assets(
    zone: str | None = Query(default=None),
    asset_type: AssetType | None = Query(default=None),
    asset_status: OperationalStatus | None = Query(default=None),
    service: MapService = Depends(get_map_service),
) -> FeatureCollection:
    return service.assets(zone=zone, asset_type=asset_type, asset_status=asset_status)


@router.get("/incidents", response_model=FeatureCollection)
def get_map_incidents(
    zone: str | None = Query(default=None),
    incident_severity: SeverityTier | None = Query(default=None),
    incident_status: IncidentStatus | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    service: MapService = Depends(get_map_service),
) -> FeatureCollection:
    return service.incidents(
        zone=zone,
        incident_severity=incident_severity,
        incident_status=incident_status,
        include_resolved=include_resolved,
    )


@router.get("/detections", response_model=FeatureCollection)
def get_map_detections(
    zone: str | None = Query(default=None),
    service: MapService = Depends(get_map_service),
) -> FeatureCollection:
    return service.detections(zone=zone)


@router.get("/summary", response_model=MapSummary)
def get_map_summary(
    zone: str | None = Query(default=None),
    asset_type: AssetType | None = Query(default=None),
    asset_status: OperationalStatus | None = Query(default=None),
    incident_severity: SeverityTier | None = Query(default=None),
    incident_status: IncidentStatus | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    service: MapService = Depends(get_map_service),
) -> MapSummary:
    return service.summary(
        zone=zone,
        asset_type=asset_type,
        asset_status=asset_status,
        incident_severity=incident_severity,
        incident_status=incident_status,
        include_resolved=include_resolved,
    )


@router.get("/nearby", response_model=NearbyResponse)
def get_map_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(500, gt=0, le=MAX_RADIUS_M),
    feature_type: str | None = Query(default=None, pattern="^(asset|pipeline|incident)$"),
    service: MapService = Depends(get_map_service),
) -> NearbyResponse:
    return service.nearby(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        feature_type=feature_type,
    )
