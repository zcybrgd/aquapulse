from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_network_health_service
from app.schemas.network_health import NetworkEventDetail, NetworkEventListResponse, NetworkSummary
from app.services.network_health import NetworkHealthService

router = APIRouter(prefix="/network-health", tags=["network-health"])


@router.get("/summary", response_model=NetworkSummary)
def get_network_summary(
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    device: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    incident: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    service: NetworkHealthService = Depends(get_network_health_service),
) -> NetworkSummary:
    return service.summary(
        event_type=event_type,
        status=status,
        device=device,
        cluster=cluster,
        incident=incident,
        start=start,
        end=end,
        search=search,
    )


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
