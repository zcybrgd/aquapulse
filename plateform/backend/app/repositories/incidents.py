from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased, contains_eager, joinedload, selectinload

from app.db.models import Asset, Incident, IncidentTimelineEvent, PipelineSegment, Zone
from app.schemas.incidents import Classification, IncidentStatus, SeverityTier, SortField, SortOrder

CLASSIFICATION_LABELS = {
    Classification.confirmed_leak.value: "Confirmed leak",
    Classification.suspected_leak.value: "Suspected leak",
    Classification.connectivity_degradation.value: "Connectivity degradation",
    Classification.sensor_fault.value: "Sensor fault",
    Classification.pressure_anomaly.value: "Pressure anomaly",
    Classification.normal_demand_spike.value: "Normal demand spike",
    Classification.insufficient_data.value: "Insufficient data",
}

STATUS_SQL = case(
    (Incident.status == IncidentStatus.awaiting_approval.value, 3),
    (Incident.status == IncidentStatus.investigating.value, 2),
    (Incident.status == IncidentStatus.resolved.value, 1),
    else_=0,
)

CLASSIFICATION_LABEL_SQL = case(
    *((Incident.classification == value, label) for value, label in CLASSIFICATION_LABELS.items()),
    else_=Incident.classification,
)

DETAIL_OPTIONS = (
    joinedload(Incident.zone),
    joinedload(Incident.pipeline_segment),
    joinedload(Incident.sensor),
    joinedload(Incident.valve),
    selectinload(Incident.telemetry_points),
    selectinload(Incident.timeline_events).joinedload(IncidentTimelineEvent.response_task),
    selectinload(Incident.response_tasks),
)


class IncidentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_incidents(
        self,
        *,
        severity: SeverityTier | None = None,
        status: IncidentStatus | None = None,
        classification: Classification | None = None,
        zone: str | None = None,
        search: str | None = None,
        sort_by: SortField = SortField.priority,
        sort_order: SortOrder = SortOrder.desc,
    ) -> list[Incident]:
        sensor = aliased(Asset)
        valve = aliased(Asset)
        stmt = (
            select(Incident)
            .join(Incident.zone)
            .outerjoin(Incident.pipeline_segment)
            .outerjoin(sensor, Incident.sensor_id == sensor.id)
            .outerjoin(valve, Incident.valve_id == valve.id)
            .options(
                contains_eager(Incident.zone),
                contains_eager(Incident.pipeline_segment),
                contains_eager(Incident.sensor, alias=sensor),
                contains_eager(Incident.valve, alias=valve),
            )
        )

        if severity is not None:
            stmt = stmt.where(Incident.severity_tier == int(severity.value.split("_")[1]))
        if status is not None:
            stmt = stmt.where(Incident.status == status.value)
        if classification is not None:
            stmt = stmt.where(Incident.classification == classification.value)
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if search and search.strip():
            stmt = stmt.where(self._search_clause(search.strip(), sensor, valve))

        descending = sort_order == SortOrder.desc
        stmt = stmt.order_by(*self._order_by(sort_by, descending))
        return list(self.session.scalars(stmt).unique().all())

    def get_by_number(self, incident_number: str) -> Incident | None:
        stmt = (
            select(Incident)
            .where(func.upper(Incident.incident_number) == incident_number.strip().upper())
            .options(*DETAIL_OPTIONS)
        )
        return self.session.scalars(stmt).unique().first()

    def _search_clause(self, needle: str, sensor: Asset, valve: Asset):
        haystack = func.lower(
            func.concat_ws(
                " ",
                Incident.incident_number,
                Incident.title,
                Zone.name,
                func.coalesce(PipelineSegment.name, ""),
                func.coalesce(sensor.external_id, ""),
                func.coalesce(valve.external_id, ""),
                func.coalesce(Incident.assigned_operator, ""),
                Incident.classification,
                CLASSIFICATION_LABEL_SQL,
            )
        )
        return haystack.like(f"%{needle.casefold()}%")

    def _order_by(self, sort_by: SortField, descending: bool):
        detected = Incident.detected_at.desc() if descending else Incident.detected_at.asc()
        if sort_by == SortField.severity:
            column = Incident.severity_tier.desc() if descending else Incident.severity_tier.asc()
            return (column, detected)
        if sort_by == SortField.status:
            column = STATUS_SQL.desc() if descending else STATUS_SQL.asc()
            return (column, detected)
        if sort_by == SortField.estimated_loss:
            column = (
                Incident.estimated_water_loss_m3.desc()
                if descending
                else Incident.estimated_water_loss_m3.asc()
            )
            return (column, detected)
        if sort_by == SortField.priority:
            severity = Incident.severity_tier.desc() if descending else Incident.severity_tier.asc()
            status = STATUS_SQL.desc() if descending else STATUS_SQL.asc()
            return (severity, status, detected)
        return (detected,)

    def next_incident_number(self) -> str:
        numbers = list(self.session.scalars(select(Incident.incident_number)).all())
        highest = 0
        for number in numbers:
            if not number or not number.upper().startswith("INC-"):
                continue
            try:
                highest = max(highest, int(number.split("-", 1)[1]))
            except ValueError:
                continue
        return f"INC-{highest + 1:04d}"

    def get_by_number_for_update(self, incident_number: str) -> Incident | None:
        """Lock the incident row for a state-changing transaction.

        Loads without joined eager options so PostgreSQL FOR UPDATE is valid.
        """
        stmt = (
            select(Incident)
            .where(func.upper(Incident.incident_number) == incident_number.strip().upper())
            .with_for_update()
        )
        return self.session.scalars(stmt).first()
