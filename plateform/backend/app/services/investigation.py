"""Human investigation workflow for detections.

Transitions live here, not in routes. Promotion is always a deliberate human
action. actor_name is a temporary development identity, not authentication.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DatabaseUnavailableError,
    DetectionConflictError,
    DetectionNotFoundError,
)
from app.db.base import utc_now
from app.db.models import Incident, IncidentTimelineEvent
from app.db.models.detection import AnomalyDetection, DetectionInvestigationEvent
from app.repositories.detections import DetectionRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.telemetry import TelemetryRepository
from app.schemas.detections import (
    AddNoteRequest,
    DetectionDetail,
    DetectionStatus,
    DismissDetectionRequest,
    InvestigationEventItem,
    InvestigationEventType,
    InvestigationHistoryResponse,
    MergeDetectionRequest,
    PromoteDetectionRequest,
    PromoteDetectionResponse,
    ReopenDetectionRequest,
    StartReviewRequest,
)
from app.schemas.incidents import IncidentStatus
from app.detection.workflow import (
    ACTIVE_STATUSES,
    DISMISS_STATUSES,
    MERGE_STATUSES,
    NOTE_STATUSES,
    START_REVIEW_STATUSES,
    TERMINAL_STATUSES,
)
from app.services.detections import DetectionService
from app.services.incidents import to_summary


class InvestigationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DetectionRepository(session)
        self.incidents = IncidentRepository(session)
        self.telemetry = TelemetryRepository(session)
        self.detections = DetectionService(session)

    def _lock(self, detection_id: str) -> AnomalyDetection:
        try:
            row = self.repository.get_by_number_for_update(detection_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise DetectionNotFoundError(detection_id)
        self.session.refresh(
            row,
            attribute_names=["sensor", "rule", "incident", "pipeline_segment", "merged_into"],
        )
        return row

    def _conflict(self, row: AnomalyDetection, *, action: str) -> None:
        if row.status == "promoted":
            incident_number = row.incident.incident_number if row.incident else None
            extra = {"incident_id": incident_number} if incident_number else None
            raise DetectionConflictError(
                "This detection has already been promoted.",
                code="detection_already_promoted",
                extra=extra,
            )
        if row.status == "merged":
            target = row.merged_into.detection_number if row.merged_into else None
            extra = {"target_detection_id": target} if target else None
            raise DetectionConflictError(
                "This detection has already been merged.",
                code="detection_already_merged",
                extra=extra,
            )
        raise DetectionConflictError(
            f"Cannot {action.replace('_', ' ')} a detection with status '{row.status}'.",
            code="invalid_detection_transition",
        )

    def _append_event(
        self,
        row: AnomalyDetection,
        *,
        event_type: str,
        actor_name: str,
        from_status: str | None,
        to_status: str | None,
        note: str | None = None,
        reason_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DetectionInvestigationEvent:
        event = DetectionInvestigationEvent(
            id=uuid4(),
            public_id=self.repository.next_event_public_id(),
            detection_id=row.id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_name=actor_name,
            note=note,
            reason_code=reason_code,
            extra_metadata=metadata or {},
            created_at=utc_now(),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _commit(self, commit: bool) -> None:
        if commit:
            self.session.commit()

    def start_review(self, detection_id: str, payload: StartReviewRequest, *, commit: bool = True) -> DetectionDetail:
        row = self._lock(detection_id)
        if row.status == "under_review":
            self._commit(commit)
            return self.detections.get_detection(detection_id)
        if row.status not in START_REVIEW_STATUSES:
            self._conflict(row, action="start_review")
        now = utc_now()
        previous = row.status
        row.status = "under_review"
        row.reviewed_by = payload.actor_name
        row.review_started_at = row.review_started_at or now
        row.updated_at = now
        self._append_event(
            row,
            event_type="review_started",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status="under_review",
            note=payload.note,
        )
        self._commit(commit)
        return self.detections.get_detection(detection_id)

    def add_note(self, detection_id: str, payload: AddNoteRequest, *, commit: bool = True) -> DetectionDetail:
        row = self._lock(detection_id)
        if row.status not in NOTE_STATUSES:
            self._conflict(row, action="add_note")
        now = utc_now()
        row.updated_at = now
        self._append_event(
            row,
            event_type="note_added",
            actor_name=payload.actor_name,
            from_status=row.status,
            to_status=row.status,
            note=payload.note,
        )
        self._commit(commit)
        return self.detections.get_detection(detection_id)

    def dismiss(self, detection_id: str, payload: DismissDetectionRequest, *, commit: bool = True) -> DetectionDetail:
        row = self._lock(detection_id)
        if row.status not in DISMISS_STATUSES:
            self._conflict(row, action="dismiss")
        now = utc_now()
        previous = row.status
        row.status = "dismissed"
        row.dismissal_reason = payload.reason_code.value
        row.dismissed_at = now
        row.resolved_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="dismissed",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status="dismissed",
            note=payload.note,
            reason_code=payload.reason_code.value,
        )
        self._commit(commit)
        return self.detections.get_detection(detection_id)

    def reopen(self, detection_id: str, payload: ReopenDetectionRequest, *, commit: bool = True) -> DetectionDetail:
        row = self._lock(detection_id)
        if row.status != "dismissed":
            self._conflict(row, action="reopen")
        now = utc_now()
        previous = row.status
        row.status = "queued"
        row.dismissal_reason = None
        row.dismissed_at = None
        row.resolved_at = None
        row.updated_at = now
        self._append_event(
            row,
            event_type="reopened",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status="queued",
            note=payload.note,
        )
        self._commit(commit)
        return self.detections.get_detection(detection_id)

    def merge(self, detection_id: str, payload: MergeDetectionRequest, *, commit: bool = True) -> DetectionDetail:
        if payload.target_detection_id.strip().upper() == detection_id.strip().upper():
            raise DetectionConflictError(
                "A detection cannot merge into itself.",
                code="detection_merge_self",
            )
        ids = sorted(
            {detection_id.strip().upper(), payload.target_detection_id.strip().upper()}
        )
        locked = {key: self._lock(key) for key in ids}
        source = locked[detection_id.strip().upper()]
        target = locked[payload.target_detection_id.strip().upper()]

        if source.status not in MERGE_STATUSES:
            self._conflict(source, action="merge")
        if target.status in TERMINAL_STATUSES or target.status == "dismissed":
            raise DetectionConflictError(
                "The merge target must be an active detection.",
                code="invalid_merge_target",
            )
        if target.status not in ACTIVE_STATUSES:
            raise DetectionConflictError(
                "The merge target must be an active detection.",
                code="invalid_merge_target",
            )
        now = utc_now()
        previous = source.status
        source.status = "merged"
        source.merged_into_detection_id = target.id
        source.resolved_at = now
        source.updated_at = now
        self._append_event(
            source,
            event_type="merged",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status="merged",
            note=payload.note,
            metadata={
                "target_detection_id": target.detection_number,
                "target_rule_code": target.rule.code if target.rule else None,
            },
        )
        self._commit(commit)
        return self.detections.get_detection(detection_id)

    def promote(
        self,
        detection_id: str,
        payload: PromoteDetectionRequest,
        *,
        commit: bool = True,
    ) -> PromoteDetectionResponse:
        row = self._lock(detection_id)
        if row.status == "promoted":
            self._conflict(row, action="promote")
        if row.status != "under_review":
            self._conflict(row, action="promote")

        sensor = row.sensor
        if sensor is None or sensor.latitude is None or sensor.longitude is None:
            raise DetectionConflictError(
                "Promotion requires a sensor location.",
                code="invalid_detection_transition",
            )
        pipeline = row.pipeline_segment or sensor.pipeline_segment
        latest = self.telemetry.latest_for_sensor(sensor.id)
        now = utc_now()
        incident_number = self.incidents.next_incident_number()
        summary_blob = row.evidence_summary or {}
        score = row.anomaly_score
        incident = Incident(
            id=uuid4(),
            incident_number=incident_number,
            organization_id=row.organization_id,
            zone_id=sensor.zone_id,
            pipeline_segment_id=pipeline.id if pipeline else None,
            sensor_id=sensor.id,
            valve_id=None,
            title=payload.title,
            classification=payload.classification.value,
            severity_tier=int(payload.severity.value.split("_")[1]),
            confidence=score,
            status=IncidentStatus.investigating.value,
            latitude=sensor.latitude,
            longitude=sensor.longitude,
            detected_at=row.detected_at,
            estimated_water_loss_m3=0,
            estimated_loss_lps=0,
            population_affected=pipeline.population_served if pipeline else 0,
            current_summary=payload.summary,
            pressure_change_pct=float((summary_blob.get("pressure") or {}).get("percent_change") or 0),
            flow_change_pct=float((summary_blob.get("flow") or {}).get("percent_change") or 0),
            network_condition=row.trigger_reason[:300],
            signal_strength_dbm=int(
                latest.signal_strength_dbm
                if latest and latest.signal_strength_dbm is not None
                else (sensor.signal_strength_dbm or 0)
            ),
            packet_loss_pct=float(latest.packet_loss_pct) if latest and latest.packet_loss_pct is not None else 0,
            assigned_operator=payload.actor_name,
            agent_investigation_summary=(
                f"No investigation agent has run. This incident was created by manual promotion "
                f"of detection {row.detection_number}."
            ),
            recommended_action=(
                "Field investigation is required. Promotion does not confirm that a leak exists."
            ),
            evidence=[
                {
                    "id": f"{incident_number}-src-detection",
                    "kind": "detection",
                    "title": "Source detection",
                    "detail": (
                        f"{row.detection_number} · {row.trigger_reason}. "
                        "Original detection evidence remains on the detection record."
                    ),
                }
            ],
            network_details={
                "source_detection_id": row.detection_number,
                "data_mode": row.data_mode,
                "promoted_by": payload.actor_name,
                "anomaly_score": score,
                "rule_code": row.rule.code if row.rule else None,
                "pressure_change_bar": 0,
                "flow_change_m3h": 0,
                "device_reachability": sensor.operational_status,
                "network_priority_status": "manual_promotion",
            },
            created_at=now,
            updated_at=now,
        )
        self.session.add(incident)
        self.session.flush()

        previous = row.status
        row.status = "promoted"
        row.incident_id = incident.id
        row.resolved_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="promoted",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status="promoted",
            note=payload.note,
            metadata={"incident_id": incident.incident_number},
        )
        self.session.add(
            IncidentTimelineEvent(
                id=uuid4(),
                incident_id=incident.id,
                timestamp=now,
                event_type="promoted_from_detection",
                title="Promoted from detection",
                description=(
                    f"{payload.actor_name} promoted {row.detection_number} after manual review. "
                    "This does not confirm that a leak exists."
                ),
                source="operator",
                status=IncidentStatus.investigating.value,
                extra_metadata={
                    "public_id": f"{incident.incident_number}-evt-1",
                    "detection_id": row.detection_number,
                },
                created_at=now,
            )
        )
        try:
            self._commit(commit)
        except Exception:
            self.session.rollback()
            raise
        detection = self.detections.get_detection(detection_id)
        created = self.incidents.get_by_number(incident_number)
        assert created is not None
        return PromoteDetectionResponse(detection=detection, incident=to_summary(created))

    def history(self, detection_id: str) -> InvestigationHistoryResponse:
        try:
            row = self.repository.get_by_number(detection_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise DetectionNotFoundError(detection_id)
        events = self.repository.list_events(row.id)
        return InvestigationHistoryResponse(
            detection_id=row.detection_number,
            events=[
                InvestigationEventItem(
                    id=event.public_id,
                    event_type=InvestigationEventType(event.event_type),
                    from_status=DetectionStatus(event.from_status) if event.from_status else None,
                    to_status=DetectionStatus(event.to_status) if event.to_status else None,
                    actor_name=event.actor_name,
                    note=event.note,
                    reason_code=event.reason_code,
                    metadata=event.extra_metadata or {},
                    created_at=event.created_at,
                    target_detection_id=(event.extra_metadata or {}).get("target_detection_id"),
                    incident_id=(event.extra_metadata or {}).get("incident_id"),
                )
                for event in events
            ],
        )
