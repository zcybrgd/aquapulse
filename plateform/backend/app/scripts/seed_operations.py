"""Idempotent Operations Center demonstration state.

Applies operational fields and response tasks to existing seeded incidents.
Does not create extra incidents or change public IDs.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.incidents import SEED_NOW
from app.db.base import utc_now
from app.db.models import Incident, IncidentTimelineEvent
from app.db.models.response_task import IncidentResponseTask

DEMO_OPERATOR = "Demo Operator"
DEMO_SUPERVISOR = "Demo Supervisor"
HARBOUR_TEAM = "Harbour Response Team"
DEMO_TASKS = {"TASK-000001", "TASK-000002", "TASK-000003"}


def _incident(session: Session, number: str) -> Incident | None:
    return session.scalar(select(Incident).where(Incident.incident_number == number))


def _add_event(
    session: Session,
    incident: Incident,
    *,
    public_id: str,
    event_type: str,
    title: str,
    description: str,
    actor_name: str,
    timestamp,
    status: str,
    task: IncidentResponseTask | None = None,
    metadata: dict | None = None,
) -> None:
    extra = dict(metadata or {})
    extra["public_id"] = public_id
    if task is not None:
        extra["response_task_id"] = task.public_id
    existing = next(
        (
            event
            for event in incident.timeline_events
            if (event.extra_metadata or {}).get("public_id") == public_id
        ),
        None,
    )
    if existing is not None:
        return
    session.add(
        IncidentTimelineEvent(
            id=uuid4(),
            incident_id=incident.id,
            timestamp=timestamp,
            event_type=event_type,
            title=title,
            description=description,
            source="operator",
            status=status,
            extra_metadata=extra,
            actor_name=actor_name,
            response_task_id=task.id if task is not None else None,
            created_at=timestamp,
        )
    )


def _get_or_create_task(session: Session, public_id: str, values: dict) -> IncidentResponseTask:
    instance = session.scalar(select(IncidentResponseTask).filter_by(public_id=public_id))
    if instance is None:
        instance = IncidentResponseTask(public_id=public_id, **values)
        session.add(instance)
        session.flush()
        return instance
    for key, value in values.items():
        setattr(instance, key, value)
    return instance


def _upsert_task(
    session: Session,
    incident: Incident,
    *,
    public_id: str,
    title: str,
    description: str,
    status: str,
    priority: str,
    assigned_to: str | None,
    created_by: str,
    due_at,
    started_at=None,
    completed_at=None,
    completed_by: str | None = None,
    completion_note: str | None = None,
) -> IncidentResponseTask:
    now = incident.updated_at or utc_now()
    return _get_or_create_task(
        session,
        public_id,
        {
            "incident_id": incident.id,
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "assigned_to": assigned_to,
            "created_by": created_by,
            "due_at": due_at,
            "started_at": started_at,
            "completed_at": completed_at,
            "completed_by": completed_by,
            "completion_note": completion_note,
            "created_at": now - timedelta(hours=2),
            "updated_at": now,
        },
    )


def seed_operations_demo(session: Session) -> None:
    extra_tasks = session.scalars(
        select(IncidentResponseTask).where(IncidentResponseTask.public_id.not_in(DEMO_TASKS))
    ).all()
    extra_ids = [task.id for task in extra_tasks]
    if extra_ids:
        for event in session.scalars(
            select(IncidentTimelineEvent).where(IncidentTimelineEvent.response_task_id.in_(extra_ids))
        ):
            event.response_task_id = None
        for task in extra_tasks:
            session.delete(task)
        session.flush()

    # Unacknowledged open incident stays INC-1838.
    acknowledged = _incident(session, "INC-1836")
    if acknowledged is not None and acknowledged.status == "open":
        when = SEED_NOW - timedelta(minutes=10)
        acknowledged.status = "acknowledged"
        acknowledged.acknowledged_at = when
        acknowledged.acknowledged_by = DEMO_OPERATOR
        acknowledged.updated_at = when
        session.flush()
        _add_event(
            session,
            acknowledged,
            public_id="INC-1836-ops-ack",
            event_type="incident_acknowledged",
            title="Incident acknowledged",
            description="Control room acknowledged the incomplete telemetry window.",
            actor_name=DEMO_OPERATOR,
            timestamp=when,
            status="acknowledged",
        )

    resolved = _incident(session, "INC-1834")
    if resolved is not None and resolved.status == "resolved":
        resolved.resolved_at = resolved.updated_at
        resolved.resolved_by = resolved.assigned_operator or "Rania Nasser"
        resolved.resolution_code = "monitoring_completed"
        resolved.resolution_summary = resolved.current_summary
        _add_event(
            session,
            resolved,
            public_id="INC-1834-ops-resolved",
            event_type="incident_resolved",
            title="Incident resolved",
            description=resolved.current_summary,
            actor_name=resolved.resolved_by,
            timestamp=resolved.updated_at,
            status="resolved",
            metadata={"resolution_code": "monitoring_completed"},
        )

    false_alarm = _incident(session, "INC-1837")
    if false_alarm is not None and false_alarm.status == "false_alarm":
        false_alarm.resolved_at = false_alarm.updated_at
        false_alarm.resolved_by = false_alarm.assigned_operator or "Yousef Al Qahtani"
        false_alarm.resolution_code = "false_alarm"
        false_alarm.resolution_summary = false_alarm.current_summary
        _add_event(
            session,
            false_alarm,
            public_id="INC-1837-ops-false",
            event_type="incident_false_alarm",
            title="Marked as false alarm",
            description="Recorded as a normal demand spike. Evidence and history were kept.",
            actor_name=false_alarm.resolved_by,
            timestamp=false_alarm.updated_at,
            status="false_alarm",
            metadata={"resolution_code": "false_alarm"},
        )

    responding = _incident(session, "INC-1842")
    if responding is None:
        return
    if responding.response_started_at is None:
        responding.response_started_at = SEED_NOW - timedelta(hours=2)
    if not responding.assigned_operator:
        responding.assigned_operator = "Layla Al Mansoori"

    overdue = _upsert_task(
        session,
        responding,
        public_id="TASK-000001",
        title="Verify isolation readiness at Harbour Segment 7",
        description=(
            "Confirm the isolation plan with the field team. This is a planning task only. "
            "Operational command integration is not enabled."
        ),
        status="in_progress",
        priority="critical",
        assigned_to=HARBOUR_TEAM,
        created_by=DEMO_SUPERVISOR,
        due_at=SEED_NOW - timedelta(hours=3),
        started_at=SEED_NOW - timedelta(hours=4),
    )
    completed = _upsert_task(
        session,
        responding,
        public_id="TASK-000002",
        title="Review corroborating pressure and flow evidence",
        description="Compare neighbouring sensors before the field crew deploys.",
        status="completed",
        priority="high",
        assigned_to="Layla Al Mansoori",
        created_by=DEMO_OPERATOR,
        due_at=SEED_NOW - timedelta(hours=1),
        started_at=SEED_NOW - timedelta(hours=3),
        completed_at=SEED_NOW - timedelta(minutes=50),
        completed_by=DEMO_OPERATOR,
        completion_note="Evidence still supports a suspected leak. No physical action was taken.",
    )
    _upsert_task(
        session,
        responding,
        public_id="TASK-000003",
        title="Brief the Harbour Response Team",
        description="Share the current summary and recommended next checks.",
        status="todo",
        priority="medium",
        assigned_to=HARBOUR_TEAM,
        created_by=DEMO_SUPERVISOR,
        due_at=SEED_NOW + timedelta(hours=4),
    )

    session.flush()
    _add_event(
        session,
        responding,
        public_id="INC-1842-ops-response",
        event_type="response_started",
        title="Response started",
        description="Coordinated response started. No physical command was executed.",
        actor_name=DEMO_SUPERVISOR,
        timestamp=responding.response_started_at or SEED_NOW,
        status="responding",
    )
    _add_event(
        session,
        responding,
        public_id="INC-1842-ops-task-1",
        event_type="response_task_started",
        title="Response task started",
        description="Started TASK-000001: Verify isolation readiness at Harbour Segment 7.",
        actor_name=DEMO_SUPERVISOR,
        timestamp=SEED_NOW - timedelta(hours=4),
        status="responding",
        task=overdue,
    )
    _add_event(
        session,
        responding,
        public_id="INC-1842-ops-task-2",
        event_type="response_task_completed",
        title="Response task completed",
        description="Completed TASK-000002 after reviewing corroborating telemetry.",
        actor_name=DEMO_OPERATOR,
        timestamp=SEED_NOW - timedelta(minutes=50),
        status="responding",
        task=completed,
    )
