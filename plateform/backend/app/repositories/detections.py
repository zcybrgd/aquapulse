from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import (
    AnomalyDetection,
    Asset,
    DetectionEvidence,
    DetectionInvestigationEvent,
    DetectionRule,
    Organization,
    Zone,
)

PRIORITY_SQL = case(
    (AnomalyDetection.priority == "critical", 4),
    (AnomalyDetection.priority == "high", 3),
    (AnomalyDetection.priority == "medium", 2),
    (AnomalyDetection.priority == "low", 1),
    else_=0,
)

ORG_SLUG = "aquapulse-demo"

DETAIL_OPTIONS = (
    joinedload(AnomalyDetection.sensor).joinedload(Asset.zone),
    joinedload(AnomalyDetection.sensor).joinedload(Asset.pipeline_segment),
    joinedload(AnomalyDetection.pipeline_segment),
    joinedload(AnomalyDetection.rule),
    joinedload(AnomalyDetection.incident),
    joinedload(AnomalyDetection.merged_into),
    selectinload(AnomalyDetection.evidence_items),
)


class DetectionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_organization(self) -> Organization | None:
        return self.session.scalar(select(Organization).where(Organization.slug == ORG_SLUG))

    def list_enabled_rules(self, *, code: str | None = None) -> list[DetectionRule]:
        stmt = select(DetectionRule).where(DetectionRule.enabled.is_(True)).order_by(DetectionRule.code)
        if code:
            stmt = stmt.where(func.upper(DetectionRule.code) == code.strip().upper())
        return list(self.session.scalars(stmt).all())

    def list_rules(self) -> list[DetectionRule]:
        return list(self.session.scalars(select(DetectionRule).order_by(DetectionRule.code, DetectionRule.version)).all())

    def list_sensors(self, *, external_id: str | None = None) -> list[Asset]:
        stmt = (
            select(Asset)
            .where(Asset.asset_type == "sensor")
            .options(joinedload(Asset.pipeline_segment), joinedload(Asset.zone))
            .order_by(Asset.external_id)
        )
        if external_id:
            stmt = stmt.where(Asset.external_id == external_id)
        return list(self.session.scalars(stmt).unique().all())

    def next_detection_number(self, organization_id: UUID) -> str:
        latest = self.session.scalar(
            select(AnomalyDetection.detection_number)
            .where(AnomalyDetection.organization_id == organization_id)
            .order_by(AnomalyDetection.detection_number.desc())
            .limit(1)
        )
        if latest and latest.startswith("DET-"):
            try:
                sequence = int(latest.split("-", 1)[1]) + 1
            except ValueError:
                sequence = 1
        else:
            sequence = 1
        return f"DET-{sequence:06d}"

    def related_for_sensor_window(
        self,
        *,
        sensor_id: UUID,
        window_start: datetime,
        window_end: datetime,
        exclude_rule_id: UUID | None = None,
    ) -> list[AnomalyDetection]:
        stmt = select(AnomalyDetection).where(
            AnomalyDetection.sensor_id == sensor_id,
            AnomalyDetection.window_start <= window_end,
            AnomalyDetection.window_end >= window_start,
        )
        if exclude_rule_id is not None:
            stmt = stmt.where(AnomalyDetection.rule_id != exclude_rule_id)
        stmt = stmt.order_by(AnomalyDetection.detected_at.desc()).limit(20)
        return list(self.session.scalars(stmt).all())

    def get_by_number(self, detection_number: str) -> AnomalyDetection | None:
        stmt = (
            select(AnomalyDetection)
            .where(func.upper(AnomalyDetection.detection_number) == detection_number.strip().upper())
            .options(*DETAIL_OPTIONS)
        )
        return self.session.scalars(stmt).unique().first()

    def list_detections(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        rule_code: str | None = None,
        sensor: str | None = None,
        zone: str | None = None,
        reason_code: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        search: str | None = None,
        sort_by: str = "detected_at",
        sort_order: str = "desc",
    ) -> list[AnomalyDetection]:
        stmt: Select = (
            select(AnomalyDetection)
            .join(AnomalyDetection.sensor)
            .join(Asset.zone)
            .join(AnomalyDetection.rule)
            .outerjoin(AnomalyDetection.pipeline_segment)
            .options(
                joinedload(AnomalyDetection.sensor).joinedload(Asset.zone),
                joinedload(AnomalyDetection.sensor).joinedload(Asset.pipeline_segment),
                joinedload(AnomalyDetection.pipeline_segment),
                joinedload(AnomalyDetection.rule),
                joinedload(AnomalyDetection.incident),
                joinedload(AnomalyDetection.merged_into),
            )
        )
        if status:
            stmt = stmt.where(AnomalyDetection.status == status)
        if priority:
            stmt = stmt.where(AnomalyDetection.priority == priority)
        if rule_code:
            stmt = stmt.where(func.upper(DetectionRule.code) == rule_code.strip().upper())
        if sensor:
            stmt = stmt.where(Asset.external_id == sensor.strip())
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if reason_code:
            stmt = stmt.where(AnomalyDetection.reason_codes.contains([reason_code]))
        if start:
            stmt = stmt.where(AnomalyDetection.detected_at >= start)
        if end:
            stmt = stmt.where(AnomalyDetection.detected_at <= end)
        if search and search.strip():
            needle = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(AnomalyDetection.detection_number).like(needle),
                    func.lower(AnomalyDetection.trigger_reason).like(needle),
                    func.lower(Asset.external_id).like(needle),
                    func.lower(Asset.name).like(needle),
                    func.lower(DetectionRule.code).like(needle),
                    func.lower(DetectionRule.name).like(needle),
                    func.lower(Zone.name).like(needle),
                )
            )

        descending = sort_order != "asc"
        if sort_by == "priority":
            order_col = PRIORITY_SQL
        elif sort_by == "score":
            order_col = AnomalyDetection.anomaly_score
        elif sort_by == "status":
            order_col = AnomalyDetection.status
        else:
            order_col = AnomalyDetection.detected_at
        stmt = stmt.order_by(order_col.desc() if descending else order_col.asc(), AnomalyDetection.detection_number.desc())
        return list(self.session.scalars(stmt).unique().all())

    def evidence_for(self, detection_id: UUID) -> list[DetectionEvidence]:
        return list(
            self.session.scalars(
                select(DetectionEvidence)
                .where(DetectionEvidence.detection_id == detection_id)
                .order_by(DetectionEvidence.created_at, DetectionEvidence.metric)
            ).all()
        )

    def map_detections(self, *, zone: str | None = None, limit: int = 200) -> list[AnomalyDetection]:
        stmt = (
            select(AnomalyDetection)
            .join(AnomalyDetection.sensor)
            .join(Asset.zone)
            .join(AnomalyDetection.rule)
            .options(
                joinedload(AnomalyDetection.sensor).joinedload(Asset.zone),
                joinedload(AnomalyDetection.pipeline_segment),
                joinedload(AnomalyDetection.rule),
            )
            .where(AnomalyDetection.status.in_(("new", "queued", "under_review")))
            .where(Asset.latitude.is_not(None), Asset.longitude.is_not(None))
            .order_by(AnomalyDetection.detected_at.desc())
            .limit(limit)
        )
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        return list(self.session.scalars(stmt).unique().all())

    def get_by_number_for_update(self, detection_number: str) -> AnomalyDetection | None:
        """Lock the detection row for a state-changing transaction.

        Loads without joined eager options so PostgreSQL FOR UPDATE is valid.
        """
        stmt = (
            select(AnomalyDetection)
            .where(func.upper(AnomalyDetection.detection_number) == detection_number.strip().upper())
            .with_for_update()
        )
        return self.session.scalars(stmt).first()

    def next_event_public_id(self) -> str:
        latest = self.session.scalar(
            select(DetectionInvestigationEvent.public_id)
            .order_by(DetectionInvestigationEvent.public_id.desc())
            .limit(1)
        )
        if latest and latest.startswith("DIE-"):
            try:
                sequence = int(latest.split("-", 1)[1]) + 1
            except ValueError:
                sequence = 1
        else:
            sequence = 1
        return f"DIE-{sequence:06d}"

    def list_events(self, detection_id: UUID) -> list[DetectionInvestigationEvent]:
        return list(
            self.session.scalars(
                select(DetectionInvestigationEvent)
                .where(DetectionInvestigationEvent.detection_id == detection_id)
                .order_by(
                    DetectionInvestigationEvent.created_at.asc(),
                    DetectionInvestigationEvent.public_id.asc(),
                )
            ).all()
        )
