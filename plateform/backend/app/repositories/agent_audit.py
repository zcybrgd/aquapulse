from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import AgentAuditEvent, AgentFinding, AgentResponseRecommendation, AgentRun
from app.db.models.detection import AnomalyDetection
from app.network.constants import MOCK_DATA_MODE


class AgentAuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_runs(
        self,
        *,
        agent_code: str | None = None,
        status: str | None = None,
        decision: str | None = None,
        incident: str | None = None,
        detection: str | None = None,
        device: str | None = None,
        cluster: str | None = None,
        data_mode: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        search: str | None = None,
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .outerjoin(AgentFinding, AgentFinding.agent_run_id == AgentRun.id)
            .outerjoin(AgentResponseRecommendation, AgentResponseRecommendation.agent_run_id == AgentRun.id)
            .outerjoin(AgentAuditEvent, AgentAuditEvent.agent_run_id == AgentRun.id)
            .options(
                joinedload(AgentRun.integration),
                selectinload(AgentRun.findings),
                selectinload(AgentRun.recommendations),
            )
        )
        if agent_code:
            stmt = stmt.where(or_(AgentRun.agent_type == agent_code, AgentAuditEvent.agent_code == agent_code))
        if status:
            stmt = stmt.where(AgentRun.status == status)
        if decision:
            stmt = stmt.where(AgentResponseRecommendation.decision == decision)
        if incident:
            pattern = f"%{incident.strip()}%"
            stmt = stmt.where(
                or_(
                    AgentRun.source_public_id.ilike(pattern),
                    AgentResponseRecommendation.mapped_incident_number.ilike(pattern),
                    AgentAuditEvent.incident_public_id.ilike(pattern),
                )
            )
        if detection:
            pattern = f"%{detection.strip()}%"
            stmt = stmt.where(
                or_(
                    AgentFinding.mapped_detection_id.ilike(pattern),
                    AgentAuditEvent.detection_public_id.ilike(pattern),
                )
            )
        if device:
            pattern = f"%{device.strip()}%"
            stmt = stmt.where(
                or_(
                    AgentFinding.mapped_valve_id.ilike(pattern),
                    AgentResponseRecommendation.mapped_device_id.ilike(pattern),
                    AgentAuditEvent.asset_public_id.ilike(pattern),
                    AgentAuditEvent.external_device_id.ilike(pattern),
                )
            )
        if cluster:
            pattern = f"%{cluster.strip()}%"
            stmt = stmt.where(
                or_(
                    AgentFinding.external_cluster_id.ilike(pattern),
                    AgentAuditEvent.external_cluster_id.ilike(pattern),
                )
            )
        if data_mode:
            stmt = stmt.where(AgentRun.data_mode == data_mode)
        else:
            stmt = stmt.where(AgentRun.data_mode != MOCK_DATA_MODE)
        if start is not None:
            stmt = stmt.where(AgentRun.started_at >= start)
        if end is not None:
            stmt = stmt.where(AgentRun.started_at <= end)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    AgentRun.public_id.ilike(pattern),
                    AgentRun.source_public_id.ilike(pattern),
                    AgentFinding.external_cluster_id.ilike(pattern),
                    AgentResponseRecommendation.decision.ilike(pattern),
                )
            )
        stmt = stmt.order_by(AgentRun.started_at.desc(), AgentRun.public_id.desc()).distinct()
        return list(self.session.scalars(stmt).unique().all())

    def get_run(self, run_id: str) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .options(
                joinedload(AgentRun.integration),
                selectinload(AgentRun.findings),
                selectinload(AgentRun.recommendations),
            )
            .where(AgentRun.public_id == run_id)
        )
        return self.session.scalars(stmt).unique().first()

    def list_events(
        self,
        *,
        agent_code: str | None = None,
        run_id: str | None = None,
        pipeline_stage: str | None = None,
        event_type: str | None = None,
        event_status: str | None = None,
        incident: str | None = None,
        detection: str | None = None,
        device: str | None = None,
        cluster: str | None = None,
        data_mode: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        search: str | None = None,
    ) -> list[AgentAuditEvent]:
        stmt = select(AgentAuditEvent).options(joinedload(AgentAuditEvent.run))
        if run_id:
            stmt = stmt.join(AgentRun, AgentAuditEvent.agent_run_id == AgentRun.id).where(AgentRun.public_id == run_id)
        if agent_code:
            stmt = stmt.where(AgentAuditEvent.agent_code == agent_code)
        if pipeline_stage:
            stmt = stmt.where(AgentAuditEvent.pipeline_stage == pipeline_stage)
        if event_type:
            stmt = stmt.where(AgentAuditEvent.event_type == event_type)
        if event_status:
            stmt = stmt.where(AgentAuditEvent.status == event_status)
        if incident:
            stmt = stmt.where(AgentAuditEvent.incident_public_id.ilike(f"%{incident.strip()}%"))
        if detection:
            stmt = stmt.where(AgentAuditEvent.detection_public_id.ilike(f"%{detection.strip()}%"))
        if device:
            stmt = stmt.where(
                or_(
                    AgentAuditEvent.asset_public_id.ilike(f"%{device.strip()}%"),
                    AgentAuditEvent.external_device_id.ilike(f"%{device.strip()}%"),
                )
            )
        if cluster:
            stmt = stmt.where(AgentAuditEvent.external_cluster_id.ilike(f"%{cluster.strip()}%"))
        if data_mode:
            stmt = stmt.where(AgentAuditEvent.data_mode == data_mode)
        else:
            stmt = stmt.where(AgentAuditEvent.data_mode != MOCK_DATA_MODE)
        if start is not None:
            stmt = stmt.where(AgentAuditEvent.occurred_at >= start)
        if end is not None:
            stmt = stmt.where(AgentAuditEvent.occurred_at <= end)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    AgentAuditEvent.public_id.ilike(pattern),
                    AgentAuditEvent.summary.ilike(pattern),
                    AgentAuditEvent.event_type.ilike(pattern),
                    AgentAuditEvent.external_cluster_id.ilike(pattern),
                    AgentAuditEvent.external_device_id.ilike(pattern),
                    AgentAuditEvent.output_summary["event_id"].astext.ilike(pattern),
                )
            )
        stmt = stmt.order_by(AgentAuditEvent.occurred_at.asc(), AgentAuditEvent.sequence_number.asc())
        return list(self.session.scalars(stmt).unique().all())

    def get_event(self, event_id: str) -> AgentAuditEvent | None:
        stmt = (
            select(AgentAuditEvent)
            .options(joinedload(AgentAuditEvent.run))
            .where(AgentAuditEvent.public_id == event_id)
        )
        found = self.session.scalars(stmt).unique().first()
        if found is not None:
            return found
        rows = self.session.scalars(select(AgentAuditEvent).options(joinedload(AgentAuditEvent.run))).unique().all()
        for row in rows:
            payload = row.output_summary or {}
            if payload.get("event_id") == event_id:
                return row
        return None

    def events_for_run(self, run_uuid) -> list[AgentAuditEvent]:
        stmt = (
            select(AgentAuditEvent)
            .options(joinedload(AgentAuditEvent.run))
            .where(AgentAuditEvent.agent_run_id == run_uuid)
            .order_by(AgentAuditEvent.sequence_number.asc(), AgentAuditEvent.occurred_at.asc())
        )
        return list(self.session.scalars(stmt).unique().all())

    def finding_for_detection(self, detection_number: str) -> AgentFinding | None:
        stmt = (
            select(AgentFinding)
            .options(joinedload(AgentFinding.run))
            .outerjoin(AnomalyDetection, AgentFinding.anomaly_detection_id == AnomalyDetection.id)
            .where(
                or_(
                    AgentFinding.mapped_detection_id == detection_number,
                    AnomalyDetection.detection_number == detection_number,
                )
            )
            .order_by(AgentFinding.created_at.desc())
        )
        return self.session.scalars(stmt).first()

    def unmapped_identity_count(self, *, data_mode: str | None = None) -> int:
        stmt = select(func.count()).select_from(AgentFinding).where(AgentFinding.mapping_status != "mapped")
        stmt = stmt.join(AgentRun, AgentFinding.agent_run_id == AgentRun.id)
        if data_mode:
            stmt = stmt.where(AgentRun.data_mode == data_mode)
        else:
            stmt = stmt.where(AgentRun.data_mode != MOCK_DATA_MODE)
        return int(self.session.scalar(stmt) or 0)
