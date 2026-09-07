from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_network_health_service
from app.schemas.network_health import (
    BulkDeviceNetworkRefreshRequest,
    BulkDeviceNetworkRefreshResponse,
    DeviceNetworkHistoryItem,
    DeviceNetworkListResponse,
    DeviceNetworkRefreshRequest,
    DeviceNetworkSnapshotDetail,
    DeviceNetworkSummary,
    NetworkEventDetail,
    NetworkEventListResponse,
)
from app.services.network_health import NetworkHealthService

router = APIRouter(prefix="/network-health", tags=["network-health"])


@router.get("/summary", response_model=DeviceNetworkSummary)
def get_network_summary(
    zone: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    reachability: str | None = Query(default=None),
    location_available: bool | None = Query(default=None),
    cellular_available: bool | None = Query(default=None),
    source_mode: str | None = Query(default=None),
    search: str | None = Query(default=None),
    service: NetworkHealthService = Depends(get_network_health_service),
) -> DeviceNetworkSummary:
    return service.device_summary(
        zone=zone,
        asset_type=asset_type,
        reachability=reachability,
        location_available=location_available,
        cellular_available=cellular_available,
        source_mode=source_mode,
        search=search,
    )


@router.get("/devices", response_model=DeviceNetworkListResponse)
def list_network_devices(
    zone: str | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    reachability: str | None = Query(default=None),
    location_available: bool | None = Query(default=None),
    cellular_available: bool | None = Query(default=None),
    source_mode: str | None = Query(default=None),
    search: str | None = Query(default=None),
    service: NetworkHealthService = Depends(get_network_health_service),
) -> DeviceNetworkListResponse:
    return service.list_devices(
        zone=zone,
        asset_type=asset_type,
        reachability=reachability,
        location_available=location_available,
        cellular_available=cellular_available,
        source_mode=source_mode,
        search=search,
    )


@router.post("/refresh", response_model=BulkDeviceNetworkRefreshResponse)
async def refresh_network_devices(
    payload: BulkDeviceNetworkRefreshRequest | None = None,
    service: NetworkHealthService = Depends(get_network_health_service),
) -> BulkDeviceNetworkRefreshResponse:
    body = payload or BulkDeviceNetworkRefreshRequest()
    return await service.refresh_many(force=body.force, asset_ids=body.asset_ids, limit=body.limit)


@router.get("/devices/{asset_id}", response_model=DeviceNetworkSnapshotDetail)
def get_network_device(
    asset_id: str,
    service: NetworkHealthService = Depends(get_network_health_service),
) -> DeviceNetworkSnapshotDetail:
    return service.get_device(asset_id)


@router.get("/devices/{asset_id}/history", response_model=list[DeviceNetworkHistoryItem])
def get_network_device_history(
    asset_id: str,
    service: NetworkHealthService = Depends(get_network_health_service),
) -> list[DeviceNetworkHistoryItem]:
    return service.device_history(asset_id)


@router.post("/devices/{asset_id}/refresh", response_model=DeviceNetworkSnapshotDetail)
async def refresh_network_device(
    asset_id: str,
    payload: DeviceNetworkRefreshRequest | None = None,
    service: NetworkHealthService = Depends(get_network_health_service),
) -> DeviceNetworkSnapshotDetail:
    body = payload or DeviceNetworkRefreshRequest()
    return await service.refresh_device(asset_id, force=body.force)


@router.get("/events", response_model=NetworkEventListResponse)
def list_network_events(
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    device: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    incident: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    service: NetworkHealthService = Depends(get_network_health_service),
) -> NetworkEventListResponse:
    return service.list_events(
        page=page,
        page_size=page_size,
        event_type=event_type,
        status=status,
        device=device,
        cluster=cluster,
        incident=incident,
        start=start,
        end=end,
        search=search,
    )


@router.get("/events/{event_id}", response_model=NetworkEventDetail)
def get_network_event(
    event_id: str,
    service: NetworkHealthService = Depends(get_network_health_service),
) -> NetworkEventDetail:
    return service.get_event(event_id)
