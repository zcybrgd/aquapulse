from fastapi import APIRouter, Depends, Query

from app.api.deps import get_operations_service
from app.schemas.incidents import (
    IncidentStatus,
    OperationsQueueResponse,
    SeverityTier,
    SortField,
    SortOrder,
)
from app.services.operations import OperationsService

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/queue", response_model=OperationsQueueResponse)
def get_operations_queue(
    severity: SeverityTier | None = Query(default=None),
    status: IncidentStatus | None = Query(default=None),
    zone: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: SortField = Query(default=SortField.priority),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    service: OperationsService = Depends(get_operations_service),
) -> OperationsQueueResponse:
    return service.queue(
        severity=severity,
        status=status,
        zone=zone,
        assigned_to=assigned_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
