from fastapi import APIRouter, Depends, Query

from app.api.deps import get_asset_service, get_maintenance_service
from app.schemas.assets import (
    AssetDetail,
    AssetHealthResponse,
    AssetIncidentListResponse,
    AssetListResponse,
    AssetSortField,
    AssetType,
    MaintenanceFilter,
    OperationalStatus,
)
from app.schemas.incidents import SortOrder
from app.schemas.maintenance import AssetMaintenanceResponse
from app.schemas.telemetry import TelemetryRange
from app.services.assets import AssetService
from app.services.maintenance import MaintenanceService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
def list_assets(
    asset_type: AssetType | None = Query(default=None),
    status: OperationalStatus | None = Query(default=None),
    zone: str | None = Query(default=None),
    search: str | None = Query(default=None),
    maintenance: MaintenanceFilter | None = Query(default=None),
    sort_by: AssetSortField = Query(default=AssetSortField.health_score),
    sort_order: SortOrder = Query(default=SortOrder.asc),
    service: AssetService = Depends(get_asset_service),
) -> AssetListResponse:
    return service.list_assets(
        asset_type=asset_type,
        status=status,
        zone=zone,
        search=search,
        maintenance=maintenance,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset_detail(
    asset_id: str,
    service: AssetService = Depends(get_asset_service),
) -> AssetDetail:
    return service.get_asset(asset_id)


@router.get("/{asset_id}/incidents", response_model=AssetIncidentListResponse)
def get_asset_incidents(
    asset_id: str,
    service: AssetService = Depends(get_asset_service),
) -> AssetIncidentListResponse:
    return service.get_related_incidents(asset_id)


@router.get("/{asset_id}/maintenance", response_model=AssetMaintenanceResponse)
def get_asset_maintenance(
    asset_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> AssetMaintenanceResponse:
    return service.asset_maintenance(asset_id)


@router.get("/{asset_id}/health", response_model=AssetHealthResponse)
def get_asset_health(
    asset_id: str,
    range: TelemetryRange = Query(default=TelemetryRange.twenty_four_hours),
    service: AssetService = Depends(get_asset_service),
) -> AssetHealthResponse:
    return service.get_health(asset_id, range.value)
