from fastapi import APIRouter, Depends, Query

from app.api.deps import get_incident_service, get_maintenance_service, get_operations_service
from app.schemas.incidents import (
    AcknowledgeRequest,
    AssignIncidentRequest,
    Classification,
    CompleteResponseTaskRequest,
    CreateResponseTaskRequest,
    FalseAlarmRequest,
    IncidentDetail,
    IncidentListResponse,
    IncidentOperationsResponse,
    IncidentStatus,
    NoteRequest,
    ReopenIncidentRequest,
    ResolveIncidentRequest,
    ResponseTaskItem,
    ResponseTaskListResponse,
    SeverityTier,
    SortField,
    SortOrder,
    TimelineResponse,
    UpdateResponseTaskRequest,
)
from app.schemas.maintenance import IncidentMaintenanceResponse
from app.services.incidents import IncidentService
from app.services.maintenance import MaintenanceService
from app.services.operations import OperationsService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
def get_incidents(
    severity: SeverityTier | None = Query(default=None),
    status: IncidentStatus | None = Query(default=None),
    classification: Classification | None = Query(default=None),
    zone: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: SortField = Query(default=SortField.priority),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    return service.list_incidents(
        severity=severity,
        status=status,
        classification=classification,
        zone=zone,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident_detail(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentDetail:
    return service.get_incident(incident_id)


@router.get("/{incident_id}/timeline", response_model=TimelineResponse)
def get_incident_timeline(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> TimelineResponse:
    return service.get_timeline(incident_id)


@router.get("/{incident_id}/maintenance", response_model=IncidentMaintenanceResponse)
def get_incident_maintenance(
    incident_id: str,
    service: MaintenanceService = Depends(get_maintenance_service),
) -> IncidentMaintenanceResponse:
    return service.incident_maintenance(incident_id)


@router.get("/{incident_id}/operations", response_model=IncidentOperationsResponse)
def get_incident_operations(
    incident_id: str,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.get_operations(incident_id)


@router.post("/{incident_id}/acknowledge", response_model=IncidentOperationsResponse)
def acknowledge_incident(
    incident_id: str,
    payload: AcknowledgeRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.acknowledge(incident_id, payload)


@router.post("/{incident_id}/assign", response_model=IncidentOperationsResponse)
def assign_incident(
    incident_id: str,
    payload: AssignIncidentRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.assign(incident_id, payload)


@router.post("/{incident_id}/start-investigation", response_model=IncidentOperationsResponse)
def start_investigation(
    incident_id: str,
    payload: NoteRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.start_investigation(incident_id, payload)


@router.post("/{incident_id}/request-approval", response_model=IncidentOperationsResponse)
def request_approval(
    incident_id: str,
    payload: NoteRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.request_approval(incident_id, payload)


@router.post("/{incident_id}/start-response", response_model=IncidentOperationsResponse)
def start_response(
    incident_id: str,
    payload: NoteRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.start_response(incident_id, payload)


@router.post("/{incident_id}/notes", response_model=IncidentOperationsResponse)
def add_operational_note(
    incident_id: str,
    payload: NoteRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.add_note(incident_id, payload)


@router.post("/{incident_id}/resolve", response_model=IncidentOperationsResponse)
def resolve_incident(
    incident_id: str,
    payload: ResolveIncidentRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.resolve(incident_id, payload)


@router.post("/{incident_id}/false-alarm", response_model=IncidentOperationsResponse)
def mark_false_alarm(
    incident_id: str,
    payload: FalseAlarmRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.false_alarm(incident_id, payload)


@router.post("/{incident_id}/reopen", response_model=IncidentOperationsResponse)
def reopen_incident(
    incident_id: str,
    payload: ReopenIncidentRequest,
    service: OperationsService = Depends(get_operations_service),
) -> IncidentOperationsResponse:
    return service.reopen(incident_id, payload)


@router.get("/{incident_id}/tasks", response_model=ResponseTaskListResponse)
def list_response_tasks(
    incident_id: str,
    service: OperationsService = Depends(get_operations_service),
) -> ResponseTaskListResponse:
    return service.list_tasks(incident_id)


@router.post("/{incident_id}/tasks", response_model=ResponseTaskItem)
def create_response_task(
    incident_id: str,
    payload: CreateResponseTaskRequest,
    service: OperationsService = Depends(get_operations_service),
) -> ResponseTaskItem:
    return service.create_task(incident_id, payload)


@router.patch("/{incident_id}/tasks/{task_id}", response_model=ResponseTaskItem)
def update_response_task(
    incident_id: str,
    task_id: str,
    payload: UpdateResponseTaskRequest,
    service: OperationsService = Depends(get_operations_service),
) -> ResponseTaskItem:
    return service.update_task(incident_id, task_id, payload)


@router.post("/{incident_id}/tasks/{task_id}/start", response_model=ResponseTaskItem)
def start_response_task(
    incident_id: str,
    task_id: str,
    payload: NoteRequest,
    service: OperationsService = Depends(get_operations_service),
) -> ResponseTaskItem:
    return service.start_task(incident_id, task_id, payload)


@router.post("/{incident_id}/tasks/{task_id}/complete", response_model=ResponseTaskItem)
def complete_response_task(
    incident_id: str,
    task_id: str,
    payload: CompleteResponseTaskRequest,
    service: OperationsService = Depends(get_operations_service),
) -> ResponseTaskItem:
    return service.complete_task(incident_id, task_id, payload)


@router.post("/{incident_id}/tasks/{task_id}/cancel", response_model=ResponseTaskItem)
def cancel_response_task(
    incident_id: str,
    task_id: str,
    payload: NoteRequest,
    service: OperationsService = Depends(get_operations_service),
) -> ResponseTaskItem:
    return service.cancel_task(incident_id, task_id, payload)
