from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseUnavailableError, IncidentNotFoundError
from app.db.models import Incident
from app.repositories.incidents import IncidentRepository
from app.schemas.incidents import (
    Classification,
    EvidenceItem,
    IncidentDetail,
    IncidentListResponse,
    IncidentStatus,
    IncidentSummary,
    IncidentTelemetryPoint,
    SeverityTier,
    SortField,
    SortOrder,
    TimelineEvent,
    TimelineResponse,
    TimelineSource,
)

from app.incident.workflow import ACTIVE_STATUSES as WORKFLOW_ACTIVE

ACTIVE_STATUSES = set(WORKFLOW_ACTIVE)


def _severity_from_tier(tier: int) -> SeverityTier:
    return SeverityTier(f"tier_{tier}")


def _network_number(details: dict, key: str, fallback: float = 0.0) -> float:
    value = details.get(key, fallback)
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def to_summary(incident: Incident) -> IncidentSummary:
    zone_name = incident.zone.name if incident.zone is not None else ""
    pipeline_name = incident.pipeline_segment.name if incident.pipeline_segment is not None else ""
    location = " · ".join(part for part in (zone_name, pipeline_name.split(" · ")[0]) if part)
    return IncidentSummary(
        id=incident.incident_number,
        incident_number=incident.incident_number,
        title=incident.title,
        classification=Classification(incident.classification),
        severity=_severity_from_tier(incident.severity_tier),
        status=IncidentStatus(incident.status),
        zone=zone_name,
        pipeline_segment=pipeline_name,
        location=location,
        detected_at=incident.detected_at,
        updated_at=incident.updated_at,
        estimated_water_loss_m3=incident.estimated_water_loss_m3,
        assigned_operator=incident.assigned_operator,
    )


def to_detail(incident: Incident) -> IncidentDetail:
    details = incident.network_details or {}
    telemetry = sorted(incident.telemetry_points, key=lambda point: point.timestamp)
    evidence_items = [
        EvidenceItem.model_validate(item) if not isinstance(item, EvidenceItem) else item
        for item in (incident.evidence or [])
    ]
    summary = to_summary(incident)
    return IncidentDetail(
        **summary.model_dump(),
        confidence=round((incident.confidence or 0) * 100, 1),
        sensor=incident.sensor.external_id if incident.sensor is not None else "",
        associated_valve=incident.valve.external_id if incident.valve is not None else "",
        latitude=incident.latitude,
        longitude=incident.longitude,
        population_affected=incident.population_affected,
        current_summary=incident.current_summary,
        pressure_change_bar=_network_number(details, "pressure_change_bar"),
        flow_change_m3h=_network_number(details, "flow_change_m3h"),
        network_condition=incident.network_condition,
        signal_strength_dbm=incident.signal_strength_dbm,
        packet_loss_percent=incident.packet_loss_pct or 0,
        device_reachability=str(details.get("device_reachability", "")),
        network_priority_status=str(details.get("network_priority_status", "")),
        agent_investigation_summary=incident.agent_investigation_summary,
        recommended_action=incident.recommended_action,
        evidence=evidence_items,
        telemetry=[
            IncidentTelemetryPoint(
                timestamp=point.timestamp,
                pressure=point.pressure,
                flow_rate=point.flow_rate,
                packet_loss=point.packet_loss_pct,
                is_detection=point.is_detection_point,
            )
            for point in telemetry
        ],
    )


def to_timeline(incident: Incident) -> TimelineResponse:
    events = sorted(incident.timeline_events, key=lambda event: event.timestamp)
    return TimelineResponse(
        incident_id=incident.incident_number,
        events=[
            TimelineEvent(
                id=str((event.extra_metadata or {}).get("public_id") or event.id),
                timestamp=event.timestamp,
                event_type=event.event_type,
                title=event.title,
                description=event.description,
                source=TimelineSource(event.source),
                status=event.status,
                actor_name=event.actor_name,
                response_task_id=(
                    event.response_task.public_id
                    if event.response_task is not None
                    else None
                ),
                metadata=dict(event.extra_metadata or {}),
            )
            for event in events
        ],
    )


class IncidentService:
    def __init__(self, session: Session) -> None:
        self.repository = IncidentRepository(session)

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
    ) -> IncidentListResponse:
        try:
            rows = self.repository.list_incidents(
                severity=severity,
                status=status,
                classification=classification,
                zone=zone,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        items = [to_summary(row) for row in rows]
        return IncidentListResponse(items=items, total=len(items))

    def get_incident(self, incident_id: str) -> IncidentDetail:
        row = self._load(incident_id)
        return to_detail(row)

    def get_timeline(self, incident_id: str) -> TimelineResponse:
        row = self._load(incident_id)
        return to_timeline(row)

    def dashboard_counts(self) -> tuple[int, int, float, int, int]:
        try:
            rows = self.repository.list_incidents()
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        active = [row for row in rows if row.status in ACTIVE_STATUSES]
        critical = [row for row in active if row.severity_tier == 3]
        water_loss = sum(row.estimated_water_loss_m3 for row in active)
        awaiting = len([row for row in active if row.status == IncidentStatus.awaiting_approval.value])
        responding = len(
            [
                row
                for row in active
                if row.status == IncidentStatus.investigating.value and row.response_started_at is not None
            ]
        )
        return len(active), len(critical), round(water_loss, 1), awaiting, responding

    def _load(self, incident_id: str) -> Incident:
        try:
            row = self.repository.get_by_number(incident_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise IncidentNotFoundError(incident_id.strip().upper())
        return row
