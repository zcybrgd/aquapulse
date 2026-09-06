from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.base import utc_now
from app.db.models import Incident
from app.db.models.response_task import IncidentResponseTask
from app.incident.workflow import OPEN_TASK_STATUSES


class ResponseTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_incident(self, incident_id) -> list[IncidentResponseTask]:
        stmt = (
            select(IncidentResponseTask)
            .where(IncidentResponseTask.incident_id == incident_id)
            .order_by(IncidentResponseTask.created_at.asc(), IncidentResponseTask.public_id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def get_by_public_id(self, public_id: str) -> IncidentResponseTask | None:
        stmt = (
            select(IncidentResponseTask)
            .options(joinedload(IncidentResponseTask.incident))
            .where(func.upper(IncidentResponseTask.public_id) == public_id.strip().upper())
        )
        return self.session.scalars(stmt).first()

    def get_by_public_id_for_update(self, public_id: str) -> IncidentResponseTask | None:
        stmt = (
            select(IncidentResponseTask)
            .where(func.upper(IncidentResponseTask.public_id) == public_id.strip().upper())
            .with_for_update()
        )
        return self.session.scalars(stmt).first()

    def next_public_id(self) -> str:
        latest = self.session.scalar(
            select(IncidentResponseTask.public_id)
            .order_by(IncidentResponseTask.public_id.desc())
            .limit(1)
        )
        highest = 0
        if latest and latest.upper().startswith("TASK-"):
            try:
                highest = int(latest.split("-", 1)[1])
            except ValueError:
                highest = 0
        return f"TASK-{highest + 1:06d}"

    def incomplete_count(self, incident_id) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(IncidentResponseTask)
                .where(
                    IncidentResponseTask.incident_id == incident_id,
                    IncidentResponseTask.status.in_(tuple(OPEN_TASK_STATUSES)),
                )
            )
            or 0
        )

    def overdue_count(self, now: datetime | None = None) -> int:
        when = now or utc_now()
        return (
            self.session.scalar(
                select(func.count())
                .select_from(IncidentResponseTask)
                .where(
                    IncidentResponseTask.status.in_(tuple(OPEN_TASK_STATUSES)),
                    IncidentResponseTask.due_at.is_not(None),
                    IncidentResponseTask.due_at < when,
                )
            )
            or 0
        )

    def list_overdue(self, *, limit: int = 12, now: datetime | None = None) -> list[IncidentResponseTask]:
        when = now or utc_now()
        stmt = (
            select(IncidentResponseTask)
            .options(joinedload(IncidentResponseTask.incident).joinedload(Incident.zone))
            .where(
                IncidentResponseTask.status.in_(tuple(OPEN_TASK_STATUSES)),
                IncidentResponseTask.due_at.is_not(None),
                IncidentResponseTask.due_at < when,
            )
            .order_by(IncidentResponseTask.due_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).unique().all())

    def list_upcoming(self, *, limit: int = 12, now: datetime | None = None) -> list[IncidentResponseTask]:
        when = now or utc_now()
        stmt = (
            select(IncidentResponseTask)
            .options(joinedload(IncidentResponseTask.incident).joinedload(Incident.zone))
            .where(
                IncidentResponseTask.status.in_(tuple(OPEN_TASK_STATUSES)),
                IncidentResponseTask.due_at.is_not(None),
                IncidentResponseTask.due_at >= when,
            )
            .order_by(IncidentResponseTask.due_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).unique().all())
