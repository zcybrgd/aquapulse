from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_maintenance_service
from app.schemas.assets import AssetType
from app.schemas.incidents import SortOrder
from app.schemas.maintenance import (
    AssignWorkOrderRequest,
    CancelWorkOrderRequest,
    CompleteWorkOrderRequest,
    CreatePlanRequest,
    CreateWorkOrderRequest,
    DisablePlanRequest,
    MaintenanceNoteRequest,
    MaintenancePlanListResponse,
    MaintenancePlanSummary,
    MaintenancePriority,
    MaintenanceSummary,
    MaintenanceType,
    RescheduleWorkOrderRequest,
    StartWorkOrderRequest,
    UpdatePlanRequest,
    UpcomingMaintenanceItem,
    WorkOrderDetail,
    WorkOrderHistoryResponse,
    WorkOrderListResponse,
    WorkOrderSortField,
    WorkOrderStatus,
)
from app.services.maintenance import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/summary", response_model=MaintenanceSummary)
def get_maintenance_summary(
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceSummary:
    return service.summary()


@router.get("/work-orders", response_model=WorkOrderListResponse)
def list_work_orders(
    status: WorkOrderStatus | None = Query(default=None),
    priority: MaintenancePriority | None = Query(default=None),
    maintenance_type: MaintenanceType | None = Query(default=None),
    asset_type: AssetType | None = Query(default=None),
    asset_id: str | None = Query(default=None),
    zone: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    due_from: datetime | None = Query(default=None),
    due_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: WorkOrderSortField = Query(default=WorkOrderSortField.due_at),
    sort_order: SortOrder = Query(default=SortOrder.asc),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderListResponse:
    return service.list_work_orders(
        status=status,
        priority=priority,
        maintenance_type=maintenance_type,
        asset_type=asset_type,
        asset_id=asset_id,
        zone=zone,
        assigned_to=assigned_to,
        overdue=overdue,
        due_from=due_from,
        due_to=due_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/work-orders/upcoming", response_model=list[UpcomingMaintenanceItem])
def list_upcoming(
    service: MaintenanceService = Depends(get_maintenance_service),
) -> list[UpcomingMaintenanceItem]:
    return service.upcoming()


@router.get("/work-orders/{work_order_id}", response_model=WorkOrderDetail)
def get_work_order(
    work_order_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.get_work_order(work_order_id)


@router.get("/work-orders/{work_order_id}/history", response_model=WorkOrderHistoryResponse)
def get_work_order_history(
    work_order_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderHistoryResponse:
    return service.get_history(work_order_id)


@router.post("/work-orders", response_model=WorkOrderDetail)
def create_work_order(
    payload: CreateWorkOrderRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.create_work_order(payload)


@router.post("/work-orders/{work_order_id}/assign", response_model=WorkOrderDetail)
def assign_work_order(
    work_order_id: str,
    payload: AssignWorkOrderRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.assign(work_order_id, payload)


@router.post("/work-orders/{work_order_id}/reschedule", response_model=WorkOrderDetail)
def reschedule_work_order(
    work_order_id: str,
    payload: RescheduleWorkOrderRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.reschedule(work_order_id, payload)


@router.post("/work-orders/{work_order_id}/start", response_model=WorkOrderDetail)
def start_work_order(
    work_order_id: str,
    payload: StartWorkOrderRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.start(work_order_id, payload)


@router.post("/work-orders/{work_order_id}/notes", response_model=WorkOrderDetail)
def add_work_order_note(
    work_order_id: str,
    payload: MaintenanceNoteRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.add_note(work_order_id, payload)


@router.post("/work-orders/{work_order_id}/complete", response_model=WorkOrderDetail)
def complete_work_order(
    work_order_id: str,
    payload: CompleteWorkOrderRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.complete(work_order_id, payload)


@router.post("/work-orders/{work_order_id}/cancel", response_model=WorkOrderDetail)
def cancel_work_order(
    work_order_id: str,
    payload: CancelWorkOrderRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> WorkOrderDetail:
    return service.cancel(work_order_id, payload)


@router.get("/plans", response_model=MaintenancePlanListResponse)
def list_plans(
    asset_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenancePlanListResponse:
    return service.list_plans(asset_id=asset_id, enabled=enabled)


@router.get("/plans/{plan_id}", response_model=MaintenancePlanSummary)
def get_plan(
    plan_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenancePlanSummary:
    return service.get_plan(plan_id)


@router.post("/plans", response_model=MaintenancePlanSummary)
def create_plan(
    payload: CreatePlanRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenancePlanSummary:
    return service.create_plan(payload)


@router.patch("/plans/{plan_id}", response_model=MaintenancePlanSummary)
def update_plan(
    plan_id: str,
    payload: UpdatePlanRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenancePlanSummary:
    return service.update_plan(plan_id, payload)


@router.post("/plans/{plan_id}/disable", response_model=MaintenancePlanSummary)
def disable_plan(
    plan_id: str,
    payload: DisablePlanRequest,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenancePlanSummary:
    return service.disable_plan(plan_id, payload)
