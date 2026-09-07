"""Human operations workflow for incidents.

Transitions live here, not in routes. No physical command is executed.
actor_name is a temporary development identity, not authentication.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DatabaseUnavailableError,
    IncidentConflictError,
    IncidentNotFoundError,
    ResponseTaskNotFoundError,
)
from app.db.base import utc_now
from app.db.models import Incident, IncidentTimelineEvent
from app.db.models.response_task import IncidentResponseTask
from app.incident.workflow import (
    ACKNOWLEDGE_STATUSES,
    ASSIGN_STATUSES,
    FALSE_ALARM_STATUSES,
    NOTE_STATUSES,
    OPEN_TASK_STATUSES,
    REOPEN_STATUSES,
    REQUEST_APPROVAL_STATUSES,
    RESOLVE_STATUSES,
    RETURN_INVESTIGATION_STATUSES,
    START_INVESTIGATION_STATUSES,
    START_RESPONSE_STATUSES,
    TERMINAL_STATUSES,
    allowed_actions,
    can_manage_tasks,
)
from app.repositories.incidents import IncidentRepository
from app.repositories.response_tasks import ResponseTaskRepository
from app.schemas.incidents import (
    AcknowledgeRequest,
    AssignIncidentRequest,
    CompleteResponseTaskRequest,
    CreateResponseTaskRequest,
    FalseAlarmRequest,
    IncidentOperationsResponse,
    IncidentStatus,
    NoteRequest,
    OperationsQueueItem,
    OperationsQueueResponse,
    OperationsSummary,
    ReopenIncidentRequest,
    ResolutionCode,
    ResolveIncidentRequest,
    ResponseTaskItem,
    ResponseTaskListResponse,
    ResponseTaskPriority,
    ResponseTaskStatus,
    SeverityTier,
    SortField,
    SortOrder,
    UpdateResponseTaskRequest,
)
from app.services.incidents import ACTIVE_STATUSES, to_summary

EVENT_TITLES = {
    "incident_acknowledged": "Incident acknowledged",
    "incident_assigned": "Incident assigned",
    "investigation_started": "Investigation started",
    "approval_requested": "Approval requested",
    "response_started": "Response started",
    "operational_note_added": "Operational note added",
    "response_task_created": "Response task created",
    "response_task_started": "Response task started",
    "response_task_completed": "Response task completed",
    "response_task_cancelled": "Response task cancelled",
    "incident_resolved": "Incident resolved",
    "incident_false_alarm": "Marked as false alarm",
    "incident_reopened": "Incident reopened",
}


def _actions_for(row: Incident) -> list[str]:
    actions = allowed_actions(row.status)
    if can_manage_tasks(row) and "manage_tasks" not in actions:
        actions.append("manage_tasks")
    return actions


class OperationsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.incidents = IncidentRepository(session)
        self.tasks = ResponseTaskRepository(session)

    def _lock_incident(self, incident_id: str) -> Incident:
        try:
            row = self.incidents.get_by_number_for_update(incident_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise IncidentNotFoundError(incident_id.strip().upper())
        self.session.refresh(row, attribute_names=["zone", "pipeline_segment", "sensor", "valve"])
        return row

    def _lock_task(self, incident_id: str, task_id: str) -> tuple[Incident, IncidentResponseTask]:
        incident = self._lock_incident(incident_id)
        try:
            task = self.tasks.get_by_public_id_for_update(task_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if task is None or task.incident_id != incident.id:
            raise ResponseTaskNotFoundError(task_id)
        return incident, task

    def _conflict(self, row: Incident, *, action: str) -> None:
        if row.status in TERMINAL_STATUSES:
            raise IncidentConflictError(
                f"Incident {row.incident_number} is already {row.status.replace('_', ' ')}.",
                code="incident_already_terminal",
            )
        raise IncidentConflictError(
            f"Cannot {action.replace('_', ' ')} an incident with status '{row.status}'.",
            code="invalid_incident_transition",
        )

    def _append_event(
        self,
        row: Incident,
        *,
        event_type: str,
        actor_name: str,
        note: str | None = None,
        task: IncidentResponseTask | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IncidentTimelineEvent:
        extra = dict(metadata or {})
        extra["public_id"] = f"{row.incident_number}-ops-{uuid4().hex[:8]}"
        if task is not None:
            extra["response_task_id"] = task.public_id
        description = note or EVENT_TITLES.get(event_type, event_type.replace("_", " ").capitalize())
        event = IncidentTimelineEvent(
            id=uuid4(),
            incident_id=row.id,
            timestamp=utc_now(),
            event_type=event_type,
            title=EVENT_TITLES.get(event_type, event_type.replace("_", " ").capitalize()),
            description=description[:1000],
            source="operator",
            status=row.status,
            extra_metadata=extra,
            actor_name=actor_name,
            response_task_id=task.id if task is not None else None,
            created_at=utc_now(),
        )
        self.session.add(event)
        return event

    def _to_task(self, task: IncidentResponseTask, *, now: datetime | None = None) -> ResponseTaskItem:
        when = now or utc_now()
        incident_number = task.incident.incident_number if task.incident is not None else ""
        overdue = (
            task.status in OPEN_TASK_STATUSES
            and task.due_at is not None
            and task.due_at < when
        )
        return ResponseTaskItem(
            id=task.public_id,
            public_id=task.public_id,
            incident_id=incident_number,
            title=task.title,
            description=task.description,
            status=ResponseTaskStatus(task.status),
            priority=ResponseTaskPriority(task.priority),
            assigned_to=task.assigned_to,
            created_by=task.created_by,
            due_at=task.due_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            completed_by=task.completed_by,
            completion_note=task.completion_note,
            created_at=task.created_at,
            updated_at=task.updated_at,
            overdue=overdue,
        )

    def _to_operations(self, row: Incident) -> IncidentOperationsResponse:
        tasks = [self._to_task(task) for task in self.tasks.list_for_incident(row.id)]
        incomplete = sum(1 for task in tasks if task.status.value in OPEN_TASK_STATUSES)
        code = ResolutionCode(row.resolution_code) if row.resolution_code else None
        return IncidentOperationsResponse(
            incident_id=row.incident_number,
            status=IncidentStatus(row.status),
            acknowledged_at=row.acknowledged_at,
            acknowledged_by=row.acknowledged_by,
            assigned_to=row.assigned_operator,
            response_started_at=row.response_started_at,
            resolved_at=row.resolved_at,
            resolved_by=row.resolved_by,
            resolution_code=code,
            resolution_summary=row.resolution_summary,
            allowed_actions=_actions_for(row),
            incomplete_task_count=incomplete,
            tasks=tasks,
        )

    def _commit(self) -> None:
        try:
            self.session.commit()
        except (OperationalError, InterfaceError) as exc:
            self.session.rollback()
            raise DatabaseUnavailableError from exc
        except Exception:
            self.session.rollback()
            raise

    def get_operations(self, incident_id: str) -> IncidentOperationsResponse:
        row = self.incidents.get_by_number(incident_id)
        if row is None:
            raise IncidentNotFoundError(incident_id.strip().upper())
        return self._to_operations(row)

    def list_tasks(self, incident_id: str) -> ResponseTaskListResponse:
        row = self.incidents.get_by_number(incident_id)
        if row is None:
            raise IncidentNotFoundError(incident_id.strip().upper())
        items = [self._to_task(task) for task in self.tasks.list_for_incident(row.id)]
        incomplete = sum(1 for item in items if item.status.value in OPEN_TASK_STATUSES)
        return ResponseTaskListResponse(
            incident_id=row.incident_number,
            items=items,
            total=len(items),
            incomplete=incomplete,
        )

    def queue(
        self,
        *,
        severity: SeverityTier | None = None,
        status: IncidentStatus | None = None,
        zone: str | None = None,
        assigned_to: str | None = None,
        search: str | None = None,
        sort_by: SortField = SortField.priority,
        sort_order: SortOrder = SortOrder.desc,
    ) -> OperationsQueueResponse:
        try:
            rows = self.incidents.list_incidents(
                severity=severity,
                status=status,
                zone=zone,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if assigned_to:
            needle = assigned_to.strip().casefold()
            rows = [
                row
                for row in rows
                if row.assigned_operator and needle in row.assigned_operator.casefold()
            ]

        now = utc_now()
        items: list[OperationsQueueItem] = []
        for row in rows:
            tasks = self.tasks.list_for_incident(row.id)
            open_tasks = [task for task in tasks if task.status in OPEN_TASK_STATUSES]
            overdue = [
                task
                for task in open_tasks
                if task.due_at is not None and task.due_at < now
            ]
            latest = f"Status {row.status.replace('_', ' ')}"
            if row.status == "awaiting_approval":
                latest = "Waiting for approval"
            latest_at = row.updated_at
            summary = to_summary(row)
            items.append(
                OperationsQueueItem(
                    **summary.model_dump(),
                    acknowledged_at=row.acknowledged_at,
                    acknowledged_by=row.acknowledged_by,
                    assigned_to=row.assigned_operator,
                    response_started_at=row.response_started_at,
                    allowed_actions=_actions_for(row),
                    open_task_count=len(open_tasks),
                    overdue_task_count=len(overdue),
                    completed_task_count=sum(1 for task in tasks if task.status == "completed"),
                    latest_update=latest,
                    latest_update_at=latest_at,
                )
            )

        all_rows = self.incidents.list_incidents()
        active = [row for row in all_rows if row.status in ACTIVE_STATUSES]
        summary = OperationsSummary(
            active_incidents=len(active),
            unacknowledged=len(
                [row for row in active if row.status == "investigating" and row.acknowledged_at is None]
            ),
            acknowledged=len(
                [row for row in active if row.status == "investigating" and row.acknowledged_at is not None]
            ),
            investigating=len([row for row in active if row.status == "investigating"]),
            awaiting_approval=len([row for row in active if row.status == "awaiting_approval"]),
            responding=len(
                [
                    row
                    for row in active
                    if row.status == "investigating" and row.response_started_at is not None
                ]
            ),
            overdue_tasks=self.tasks.overdue_count(now),
            critical_active=len([row for row in active if row.severity_tier == 3]),
        )
        return OperationsQueueResponse(
            items=items,
            total=len(items),
            summary=summary,
            overdue_tasks=[self._to_task(task, now=now) for task in self.tasks.list_overdue(now=now)],
            upcoming_tasks=[self._to_task(task, now=now) for task in self.tasks.list_upcoming(now=now)],
        )

    def overdue_task_count(self) -> int:
        try:
            return self.tasks.overdue_count()
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc

    def acknowledge(self, incident_id: str, payload: AcknowledgeRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status == IncidentStatus.investigating.value and row.acknowledged_at is not None:
            self.session.rollback()
            return self.get_operations(incident_id)
        if row.status not in ACKNOWLEDGE_STATUSES:
            self._conflict(row, action="acknowledge")
        now = utc_now()
        row.acknowledged_at = now
        row.acknowledged_by = payload.actor_name
        row.updated_at = now
        self._append_event(
            row,
            event_type="incident_acknowledged",
            actor_name=payload.actor_name,
            note=payload.note or f"{payload.actor_name} acknowledged the incident.",
        )
        self._commit()
        return self.get_operations(incident_id)

    def assign(self, incident_id: str, payload: AssignIncidentRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in ASSIGN_STATUSES:
            self._conflict(row, action="assign")
        row.assigned_operator = payload.assigned_to
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="incident_assigned",
            actor_name=payload.actor_name,
            note=payload.note or f"Assigned to {payload.assigned_to}.",
            metadata={"assigned_to": payload.assigned_to},
        )
        self._commit()
        return self.get_operations(incident_id)

    def start_investigation(self, incident_id: str, payload: NoteRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        returning = row.status in RETURN_INVESTIGATION_STATUSES
        if row.status == IncidentStatus.investigating.value:
            self.session.rollback()
            return self.get_operations(incident_id)
        if row.status not in START_INVESTIGATION_STATUSES and not returning:
            self._conflict(row, action="start_investigation")
        row.status = IncidentStatus.investigating.value
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="investigation_started",
            actor_name=payload.actor_name,
            note=payload.note
            or (
                f"{payload.actor_name} returned the incident to investigation."
                if returning
                else f"{payload.actor_name} started investigation."
            ),
        )
        self._commit()
        return self.get_operations(incident_id)

    def request_approval(self, incident_id: str, payload: NoteRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in REQUEST_APPROVAL_STATUSES:
            self._conflict(row, action="request_approval")
        row.status = IncidentStatus.awaiting_approval.value
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="approval_requested",
            actor_name=payload.actor_name,
            note=payload.note or f"{payload.actor_name} requested operational approval.",
        )
        self._commit()
        return self.get_operations(incident_id)

    def start_response(self, incident_id: str, payload: NoteRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in START_RESPONSE_STATUSES:
            self._conflict(row, action="start_response")
        if (
            row.status == IncidentStatus.investigating.value
            and row.response_started_at is not None
        ):
            self.session.rollback()
            return self.get_operations(incident_id)
        if not row.assigned_operator:
            raise IncidentConflictError(
                "Assign an operator or team before starting the response.",
                code="incident_assignment_required",
            )
        now = utc_now()
        if row.status == IncidentStatus.awaiting_approval.value:
            row.status = IncidentStatus.investigating.value
        if row.response_started_at is None:
            row.response_started_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="response_started",
            actor_name=payload.actor_name,
            note=payload.note
            or f"{payload.actor_name} started a coordinated response. No physical command was executed.",
        )
        self._commit()
        return self.get_operations(incident_id)

    def add_note(self, incident_id: str, payload: NoteRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in NOTE_STATUSES:
            self._conflict(row, action="add_note")
        if not payload.note:
            raise IncidentConflictError(
                "An operational note is required.",
                code="invalid_incident_transition",
            )
        previous = row.status
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="operational_note_added",
            actor_name=payload.actor_name,
            note=payload.note,
            metadata={"from_status": previous, "to_status": previous},
        )
        self._commit()
        return self.get_operations(incident_id)

    def resolve(self, incident_id: str, payload: ResolveIncidentRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in RESOLVE_STATUSES:
            self._conflict(row, action="resolve")
        incomplete = self.tasks.incomplete_count(row.id)
        if incomplete and not payload.confirm_incomplete_tasks:
            raise IncidentConflictError(
                f"{incomplete} response task(s) are still open. Confirm to resolve anyway.",
                code="incident_incomplete_tasks",
                extra={"incomplete_task_count": incomplete},
            )
        now = utc_now()
        row.status = IncidentStatus.resolved.value
        row.resolved_at = now
        row.resolved_by = payload.actor_name
        row.resolution_code = payload.resolution_code.value
        row.resolution_summary = payload.resolution_summary
        row.updated_at = now
        self._append_event(
            row,
            event_type="incident_resolved",
            actor_name=payload.actor_name,
            note=payload.resolution_summary,
            metadata={"resolution_code": payload.resolution_code.value},
        )
        self._commit()
        return self.get_operations(incident_id)

    def false_alarm(self, incident_id: str, payload: FalseAlarmRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in FALSE_ALARM_STATUSES:
            self._conflict(row, action="mark_false_alarm")
        now = utc_now()
        row.status = IncidentStatus.resolved.value
        row.resolved_at = now
        row.resolved_by = payload.actor_name
        row.resolution_code = ResolutionCode.false_alarm.value
        row.resolution_summary = payload.resolution_summary
        row.updated_at = now
        self._append_event(
            row,
            event_type="incident_false_alarm",
            actor_name=payload.actor_name,
            note=payload.note or payload.resolution_summary,
            metadata={"resolution_code": ResolutionCode.false_alarm.value},
        )
        self._commit()
        return self.get_operations(incident_id)

    def reopen(self, incident_id: str, payload: ReopenIncidentRequest) -> IncidentOperationsResponse:
        row = self._lock_incident(incident_id)
        if row.status not in REOPEN_STATUSES:
            self._conflict(row, action="reopen")
        row.status = IncidentStatus.investigating.value
        row.resolved_at = None
        row.resolved_by = None
        row.resolution_code = None
        row.resolution_summary = None
        row.acknowledged_at = None
        row.acknowledged_by = None
        row.response_started_at = None
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="incident_reopened",
            actor_name=payload.actor_name,
            note=payload.note or f"{payload.actor_name} reopened the incident.",
        )
        self._commit()
        return self.get_operations(incident_id)

    def create_task(self, incident_id: str, payload: CreateResponseTaskRequest) -> ResponseTaskItem:
        row = self._lock_incident(incident_id)
        if not can_manage_tasks(row):
            self._conflict(row, action="manage_tasks")
        now = utc_now()
        task = IncidentResponseTask(
            id=uuid4(),
            public_id=self.tasks.next_public_id(),
            incident_id=row.id,
            title=payload.title,
            description=payload.description,
            status=ResponseTaskStatus.todo.value,
            priority=payload.priority.value,
            assigned_to=payload.assigned_to,
            created_by=payload.actor_name,
            due_at=payload.due_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(task)
        self.session.flush()
        row.updated_at = now
        self._append_event(
            row,
            event_type="response_task_created",
            actor_name=payload.actor_name,
            note=f"Created task {task.public_id}: {task.title}.",
            task=task,
        )
        self._commit()
        self.session.refresh(task)
        task.incident = row
        return self._to_task(task)

    def update_task(
        self,
        incident_id: str,
        task_id: str,
        payload: UpdateResponseTaskRequest,
    ) -> ResponseTaskItem:
        row, task = self._lock_task(incident_id, task_id)
        if not can_manage_tasks(row):
            self._conflict(row, action="manage_tasks")
        if task.status not in OPEN_TASK_STATUSES:
            raise IncidentConflictError(
                "A completed or cancelled task cannot be edited.",
                code="invalid_task_transition",
            )
        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.priority is not None:
            task.priority = payload.priority.value
        if payload.assigned_to is not None:
            task.assigned_to = payload.assigned_to
        if payload.due_at is not None:
            task.due_at = payload.due_at
        task.updated_at = utc_now()
        row.updated_at = task.updated_at
        self._commit()
        task.incident = row
        return self._to_task(task)

    def start_task(self, incident_id: str, task_id: str, payload: NoteRequest) -> ResponseTaskItem:
        row, task = self._lock_task(incident_id, task_id)
        if not can_manage_tasks(row):
            self._conflict(row, action="manage_tasks")
        if task.status != ResponseTaskStatus.todo.value:
            raise IncidentConflictError(
                f"Cannot start a task with status '{task.status}'.",
                code="invalid_task_transition",
            )
        now = utc_now()
        task.status = ResponseTaskStatus.in_progress.value
        task.started_at = now
        task.updated_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="response_task_started",
            actor_name=payload.actor_name,
            note=payload.note or f"Started task {task.public_id}.",
            task=task,
        )
        self._commit()
        task.incident = row
        return self._to_task(task)

    def complete_task(
        self,
        incident_id: str,
        task_id: str,
        payload: CompleteResponseTaskRequest,
    ) -> ResponseTaskItem:
        row, task = self._lock_task(incident_id, task_id)
        if not can_manage_tasks(row):
            self._conflict(row, action="manage_tasks")
        if task.status not in OPEN_TASK_STATUSES:
            raise IncidentConflictError(
                f"Cannot complete a task with status '{task.status}'.",
                code="invalid_task_transition",
            )
        now = utc_now()
        task.status = ResponseTaskStatus.completed.value
        if task.started_at is None:
            task.started_at = now
        task.completed_at = now
        task.completed_by = payload.actor_name
        task.completion_note = payload.completion_note
        task.updated_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="response_task_completed",
            actor_name=payload.actor_name,
            note=payload.completion_note or f"Completed task {task.public_id}.",
            task=task,
        )
        self._commit()
        task.incident = row
        return self._to_task(task)

    def cancel_task(self, incident_id: str, task_id: str, payload: NoteRequest) -> ResponseTaskItem:
        row, task = self._lock_task(incident_id, task_id)
        if not can_manage_tasks(row):
            self._conflict(row, action="manage_tasks")
        if task.status not in OPEN_TASK_STATUSES:
            raise IncidentConflictError(
                f"Cannot cancel a task with status '{task.status}'.",
                code="invalid_task_transition",
            )
        now = utc_now()
        task.status = ResponseTaskStatus.cancelled.value
        task.updated_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="response_task_cancelled",
            actor_name=payload.actor_name,
            note=payload.note or f"Cancelled task {task.public_id}.",
            task=task,
        )
        self._commit()
        task.incident = row
        return self._to_task(task)
