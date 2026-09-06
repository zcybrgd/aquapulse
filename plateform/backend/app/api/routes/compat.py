from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_compat_service
from app.schemas.integrations import (
    CompatNotifyResponse,
    CompatQodResponse,
    CompatReachability,
    CompatValveIsolateResponse,
    CompatValveStatusResponse,
)
from app.services.compat import CompatibilityService

router = APIRouter(prefix="/integrations/compat", tags=["integration-compat"])


@router.get("/v1/device-reachability/{device_id}", response_model=CompatReachability)
def device_reachability(
    device_id: str,
    service: CompatibilityService = Depends(get_compat_service),
) -> CompatReachability:
    return service.reachability(device_id)


@router.post("/v1/qod/{device_id}/reserve", response_model=CompatQodResponse)
def reserve_qod(
    device_id: str,
    service: CompatibilityService = Depends(get_compat_service),
) -> CompatQodResponse:
    return service.reserve_qod(device_id)


@router.post("/v1/notify", response_model=CompatNotifyResponse)
def notify(
    payload: dict[str, Any],
    service: CompatibilityService = Depends(get_compat_service),
) -> CompatNotifyResponse:
    return service.notify(payload)


@router.post("/v1/valve/isolate", response_model=CompatValveIsolateResponse)
def isolate_valve(
    payload: dict[str, Any] | None = None,
    service: CompatibilityService = Depends(get_compat_service),
) -> CompatValveIsolateResponse:
    return service.isolate_valve(payload)


@router.get("/v1/valve/status/{device_id}", response_model=CompatValveStatusResponse)
def valve_status(
    device_id: str,
    service: CompatibilityService = Depends(get_compat_service),
) -> CompatValveStatusResponse:
    return service.valve_status(device_id)
