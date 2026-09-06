from datetime import datetime, timezone

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseUnavailableError, DetectionNotFoundError
from app.db.models.detection import AnomalyDetection, DetectionEvidence
from app.repositories.agent_audit import AgentAuditRepository
from app.repositories.detections import DetectionRepository
from app.repositories.telemetry import TelemetryRepository
from app.schemas.detections import (
    AgentNetworkMetadata,
    AgentPipelineContext,
    AgentRuleTrigger,
    AgentSensorIdentity,
    DetectionDetail,
    DetectionEvidenceItem,
    DetectionEvidenceResponse,
    DetectionListResponse,
    DetectionPriority,
    DetectionQueueStats,
    DetectionSortField,
    DetectionStatus,
    DetectionSummary,
    InvestigationAgentInputV1,
    SortOrder,
    TelemetryWindow,
)
from app.services.telemetry import classify_freshness
from app.services.telemetry_constants import DATA_MODE
from app.db.base import utc_now
from app.detection.workflow import allowed_actions


def _evidence_item(row: DetectionEvidence) -> DetectionEvidenceItem:
    return DetectionEvidenceItem(
        metric=row.metric,
        observed_value=row.observed_value,
        baseline_value=row.baseline_value,
        threshold_value=row.threshold_value,
        unit=row.unit,
        evidence_type=row.evidence_type,
        reading_start_time=row.reading_start_time,
        reading_end_time=row.reading_end_time,
        details=row.details or {},
    )


class DetectionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DetectionRepository(session)
        self.telemetry = TelemetryRepository(session)
        self.audit = AgentAuditRepository(session)

    def _to_summary(self, row: AnomalyDetection) -> DetectionSummary:
        sensor = row.sensor
        zone = sensor.zone.name if sensor and sensor.zone else ""
        pipeline = None
        if row.pipeline_segment:
            pipeline = row.pipeline_segment.name
        elif sensor and sensor.pipeline_segment:
            pipeline = sensor.pipeline_segment.name
        incident_number = row.incident.incident_number if row.incident else None
        merged_number = row.merged_into.detection_number if row.merged_into else None
        finding = self.audit.finding_for_detection(row.detection_number)
        awaiting = finding is None and row.status in {"new", "queued"}
        return DetectionSummary(
            id=row.detection_number,
            detection_number=row.detection_number,
            status=DetectionStatus(row.status),
            priority=DetectionPriority(row.priority),
            anomaly_score=row.anomaly_score,
            trigger_reason=row.trigger_reason,
            reason_codes=list(row.reason_codes or []),
            rule_code=row.rule.code,
            rule_name=row.rule.name,
            rule_version=row.rule_version,
            sensor_id=sensor.external_id if sensor else "",
            sensor_name=sensor.name if sensor else "",
            zone=zone,
            pipeline_segment=pipeline,
            detected_at=row.detected_at,
            window_start=row.window_start,
            window_end=row.window_end,
            data_mode=row.data_mode,
            incident_id=incident_number,
            reviewed_by=row.reviewed_by,
            review_started_at=row.review_started_at,
            dismissed_at=row.dismissed_at,
            dismissal_reason=row.dismissal_reason,
            merged_into_detection_id=merged_number,
            resolved_at=row.resolved_at,
            updated_at=row.updated_at,
            allowed_actions=allowed_actions(row.status),
            screening_priority_label="Screening priority",
            awaiting_agent_investigation=awaiting,
            has_agent_finding=finding is not None,
        )

    def list_detections(
        self,
        *,
        status: DetectionStatus | None = None,
        priority: DetectionPriority | None = None,
        rule_code: str | None = None,
        sensor: str | None = None,
        zone: str | None = None,
        reason_code: str | None = None,
        start=None,
        end=None,
        search: str | None = None,
        sort_by: DetectionSortField = DetectionSortField.detected_at,
        sort_order: SortOrder = SortOrder.desc,
    ) -> DetectionListResponse:
        try:
            rows = self.repository.list_detections(
                status=status.value if status else None,
                priority=priority.value if priority else None,
                rule_code=rule_code,
                sensor=sensor,
                zone=zone,
                reason_code=reason_code,
                start=start,
                end=end,
                search=search,
                sort_by=sort_by.value,
                sort_order=sort_order.value,
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        return DetectionListResponse(
            items=[self._to_summary(row) for row in rows],
            total=len(rows),
            data_mode=DATA_MODE,
        )

    def get_detection(self, detection_id: str) -> DetectionDetail:
        try:
            row = self.repository.get_by_number(detection_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise DetectionNotFoundError(detection_id)
        sensor = row.sensor
        latest = self.telemetry.latest_for_sensor(sensor.id)
        now = utc_now()
        freshness = classify_freshness(latest.time if latest else None, now)
        related_rows = self.repository.related_for_sensor_window(
            sensor_id=sensor.id,
            window_start=row.window_start,
            window_end=row.window_end,
            exclude_rule_id=row.rule_id,
        )
        related = [self._to_summary(item) for item in related_rows if item.id != row.id]
        pipeline = row.pipeline_segment or (sensor.pipeline_segment if sensor else None)
        summary = row.evidence_summary or {}
        finding = self.audit.finding_for_detection(row.detection_number)
        agent_finding = None
        if finding is not None:
            raw = finding.raw_finding or {}
            agent_finding = {
                "classification": finding.classification,
                "severity_tier": finding.severity_tier,
                "confidence_score": finding.confidence_score,
                "anomaly_score": raw.get("anomaly_score"),
                "operator_justification": finding.operator_justification,
                "mapping_status": finding.mapping_status,
                "run_id": finding.run.public_id if finding.run is not None else None,
                "external_cluster_id": finding.external_cluster_id,
            }
        return DetectionDetail(
            id=row.detection_number,
            detection_number=row.detection_number,
            status=DetectionStatus(row.status),
            priority=DetectionPriority(row.priority),
            anomaly_score=row.anomaly_score,
            trigger_reason=row.trigger_reason,
            reason_codes=list(row.reason_codes or []),
            rule_code=row.rule.code,
            rule_name=row.rule.name,
            rule_version=row.rule_version,
            sensor_id=sensor.external_id,
            sensor_name=sensor.name,
            asset_status=sensor.operational_status,
            zone=sensor.zone.name if sensor.zone else "",
            pipeline_segment=pipeline.name if pipeline else None,
            pipeline_segment_id=pipeline.external_id if pipeline else None,
            criticality=pipeline.criticality_score if pipeline else None,
            population_served=pipeline.population_served if pipeline else None,
            detected_at=row.detected_at,
            window_start=row.window_start,
            window_end=row.window_end,
            reading_count=row.reading_count,
            correlation_key=row.correlation_key,
            score_explanation=summary.get("score") or {},
            evidence_summary=summary,
            evidence=[_evidence_item(item) for item in row.evidence_items],
            related_detections=related,
            incident_id=row.incident.incident_number if row.incident else None,
            telemetry_freshness=freshness.value if hasattr(freshness, "value") else str(freshness),
            latest_reading_at=latest.time if latest else None,
            data_mode=row.data_mode,
            reviewed_by=row.reviewed_by,
            review_started_at=row.review_started_at,
            dismissed_at=row.dismissed_at,
            dismissal_reason=row.dismissal_reason,
            merged_into_detection_id=row.merged_into.detection_number if row.merged_into else None,
            resolved_at=row.resolved_at,
            updated_at=row.updated_at,
            allowed_actions=allowed_actions(row.status),
            screening_priority_label="Screening priority",
            awaiting_agent_investigation=finding is None and row.status in {"new", "queued"},
            has_agent_finding=finding is not None,
            agent_finding=agent_finding,
        )

    def get_evidence(self, detection_id: str) -> DetectionEvidenceResponse:
        try:
            row = self.repository.get_by_number(detection_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise DetectionNotFoundError(detection_id)
        items = self.repository.evidence_for(row.id)
        return DetectionEvidenceResponse(
            detection_id=row.detection_number,
            items=[_evidence_item(item) for item in items],
            data_mode=row.data_mode,
        )

    def summary(self) -> DetectionQueueStats:
        try:
            rows = self.repository.list_detections()
            organization = self.repository.get_organization()
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        last_run = (organization.settings or {}).get("last_detection_run") if organization else None
        last_run_at = None
        if last_run and last_run.get("finished_at"):
            raw = last_run["finished_at"]
            last_run_at = datetime.fromisoformat(raw.replace("Z", "+00:00")) if isinstance(raw, str) else raw
        highest = None
        ranked = sorted(
            rows,
            key=lambda item: (
                {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(item.priority, 0),
                item.anomaly_score,
            ),
            reverse=True,
        )
        if ranked:
            highest = self._to_summary(ranked[0])
        return DetectionQueueStats(
            new=sum(1 for item in rows if item.status == "new"),
            queued=sum(1 for item in rows if item.status == "queued"),
            under_review=sum(1 for item in rows if item.status == "under_review"),
            high_priority=sum(1 for item in rows if item.priority == "high"),
            critical_priority=sum(1 for item in rows if item.priority == "critical"),
            total=len(rows),
            last_run_at=last_run_at,
            last_run_deduplicated=last_run.get("deduplicated") if last_run else None,
            highest_priority=highest,
            data_mode=DATA_MODE,
        )

    def agent_input(self, detection_id: str) -> InvestigationAgentInputV1:
        detail = self.get_detection(detection_id)
        try:
            row = self.repository.get_by_number(detection_id)
            latest = self.telemetry.latest_for_sensor(row.sensor.id) if row else None
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        assert row is not None
        return InvestigationAgentInputV1(
            detection_id=detail.detection_number,
            detected_at=detail.detected_at,
            telemetry_window=TelemetryWindow(start=detail.window_start, end=detail.window_end),
            recent_readings_reference={
                "store": "sensor_readings",
                "sensor_id": detail.sensor_id,
                "window_start": detail.window_start.astimezone(timezone.utc).isoformat(),
                "window_end": detail.window_end.astimezone(timezone.utc).isoformat(),
                "reading_count": detail.reading_count,
            },
            sensor=AgentSensorIdentity(
                id=detail.sensor_id,
                name=detail.sensor_name,
                operational_status=detail.asset_status,
                manufacturer=row.sensor.manufacturer,
                model=row.sensor.model,
            ),
            network_metadata=AgentNetworkMetadata(
                zone=detail.zone,
                signal_strength_dbm=latest.signal_strength_dbm if latest else None,
                packet_loss_pct=latest.packet_loss_pct if latest else None,
                telemetry_freshness=detail.telemetry_freshness,
                latest_reading_at=detail.latest_reading_at,
            ),
            rule_triggers=[
                AgentRuleTrigger(
                    rule_code=detail.rule_code,
                    rule_name=detail.rule_name,
                    rule_version=detail.rule_version,
                    reason_codes=detail.reason_codes,
                    trigger_reason=detail.trigger_reason,
                    threshold=row.rule.threshold,
                    secondary_threshold=row.rule.secondary_threshold,
                )
            ],
            structured_evidence=detail.evidence,
            pipeline_context=AgentPipelineContext(
                segment_id=detail.pipeline_segment_id,
                segment_name=detail.pipeline_segment,
                criticality=detail.criticality,
                population_served=detail.population_served,
            ),
            criticality=detail.criticality,
            population_served=detail.population_served,
            current_asset_status=detail.asset_status,
            data_mode=detail.data_mode,
        )
