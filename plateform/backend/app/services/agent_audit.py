from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AgentAuditEventNotFoundError, AgentAuditRunNotFoundError
from app.data.incidents import SEED_NOW
from app.db.models import AgentAuditEvent, AgentRun
from app.integrations.sanitize import sanitize_payload
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT
from app.repositories.agent_audit import AgentAuditRepository
from app.schemas.agent_audit import (
    AgentAuditEventDetail,
    AgentAuditEventListResponse,
    AgentAuditEventSummary,
    AgentAuditRunDetail,
    AgentAuditRunListResponse,
    AgentAuditRunSummary,
    AgentAuditSummary,
    AgentCount,
    LinkedFinding,
)


def _reasoning_summary(trace: Any) -> str | None:
    if trace is None:
        return None
    if isinstance(trace, str):
        return trace.strip() or None
    if isinstance(trace, dict):
        for key in ("summary", "headline", "text"):
            value = trace.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return _reasoning_summary(trace.get("steps"))
    if isinstance(trace, list):
        parts = []
        for item in trace:
            if isinstance(item, dict):
                label = item.get("step") or item.get("summary") or item.get("node")
                if isinstance(label, str) and label.strip():
                    parts.append(label.strip())
            elif isinstance(item, str) and item.strip():
                parts.append(item.strip())
        return " → ".join(parts[:6]) if parts else None
    return None


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(items)
    start = max(0, (page - 1) * page_size)
    return items[start : start + page_size], total


class AgentAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AgentAuditRepository(session)

    def _to_event_summary(self, event: AgentAuditEvent) -> AgentAuditEventSummary:
        return AgentAuditEventSummary(
            id=str(event.id),
            public_id=event.public_id,
            agent_run_id=event.run.public_id if event.run is not None else None,
            agent_code=event.agent_code,
            contract_version=event.contract_version,
            pipeline_stage=event.pipeline_stage,
            node_name=event.node_name,
            sequence_number=event.sequence_number,
            event_type=event.event_type,
            status=event.status,
            summary=event.summary,
            incident_public_id=event.incident_public_id,
            detection_public_id=event.detection_public_id,
            asset_public_id=event.asset_public_id,
            external_cluster_id=event.external_cluster_id,
            external_device_id=event.external_device_id,
            error_code=event.error_code,
            error_message=event.error_message,
            duration_ms=event.duration_ms,
            data_mode=event.data_mode,
            occurred_at=event.occurred_at,
            reasoning_summary=_reasoning_summary(event.reasoning_trace),
        )

    def _to_event_detail(self, event: AgentAuditEvent) -> AgentAuditEventDetail:
        summary = self._to_event_summary(event)
        return AgentAuditEventDetail(
            **summary.model_dump(),
            input_summary=sanitize_payload(event.input_summary or {}),
            output_summary=sanitize_payload(event.output_summary or {}),
            reasoning_trace=sanitize_payload(event.reasoning_trace),
            safety_checks=sanitize_payload(event.safety_checks),
        )

    def _to_run_summary(self, run: AgentRun, events: list[AgentAuditEvent] | None = None) -> AgentAuditRunSummary:
        timeline = events if events is not None else self.repository.events_for_run(run.id)
        stages = list(dict.fromkeys(event.pipeline_stage for event in timeline))
        incident = next((event.incident_public_id for event in timeline if event.incident_public_id), None)
        detection = next((event.detection_public_id for event in timeline if event.detection_public_id), None)
        device = next((event.external_device_id or event.asset_public_id for event in timeline if event.external_device_id or event.asset_public_id), None)
        cluster = next((event.external_cluster_id for event in timeline if event.external_cluster_id), None)
        classification = run.findings[0].classification if run.findings else None
        severity = run.findings[0].severity_tier if run.findings else None
        mapping = run.findings[0].mapping_status if run.findings else None
        decision = run.recommendations[0].decision if run.recommendations else None
        if run.recommendations:
            incident = incident or run.recommendations[0].mapped_incident_number
            device = device or run.recommendations[0].mapped_device_id or run.recommendations[0].external_device_id
        if run.findings:
            cluster = cluster or run.findings[0].external_cluster_id
            detection = detection or run.findings[0].mapped_detection_id
            device = device or run.findings[0].external_valve_id
        blocked = any(event.status == "blocked" or event.pipeline_stage == "platform_safety" and event.status == "blocked" for event in timeline)
        blocked = blocked or any(rec.safety_status == "blocked" for rec in run.recommendations)
        contract = run.contract_version
        return AgentAuditRunSummary(
            id=str(run.id),
            public_id=run.public_id,
            agent_code=run.integration.agent_code if run.integration is not None else run.agent_type,
            agent_type=run.agent_type,
            contract_version=contract,
            pipeline_stages=stages,
            source_type=run.source_type,
            source_public_id=run.source_public_id,
            status=run.status,
            classification=classification,
            investigation_severity=severity,
            decision=decision,
            duration_ms=run.duration_ms,
            started_at=run.started_at,
            related_incident=incident,
            related_detection=detection,
            related_device=device,
            external_cluster_id=cluster,
            data_mode=run.data_mode,
            blocked=blocked,
            contract_unconfirmed=contract in {NETWORK_CONTRACT, "unconfirmed"} or run.agent_type == NETWORK_AGENT_CODE,
            mapping_status=mapping,
        )

    def summary(self, **filters) -> AgentAuditSummary:
        runs = self.repository.list_runs(**filters)
        by_agent: dict[str, int] = {}
        stages: dict[str, int] = {}
        blocked = 0
        durations: list[int] = []
        last_run = None
        successful = 0
        failed = 0
        for run in runs:
            events = self.repository.events_for_run(run.id)
            item = self._to_run_summary(run, events)
            by_agent[item.agent_code] = by_agent.get(item.agent_code, 0) + 1
            for stage in item.pipeline_stages:
                stages[stage] = stages.get(stage, 0) + 1
            if item.blocked:
                blocked += 1
            if run.duration_ms is not None:
                durations.append(run.duration_ms)
            if run.status == "succeeded":
                successful += 1
            if run.status in {"failed", "rejected"}:
                failed += 1
            if last_run is None or run.started_at > last_run:
                last_run = run.started_at
        return AgentAuditSummary(
            total_runs=len(runs),
            successful_runs=successful,
            failed_runs=failed,
            blocked_actions=blocked,
            average_duration_ms=round(sum(durations) / len(durations), 2) if durations else None,
            runs_by_agent=[AgentCount(key=key, count=value) for key, value in sorted(by_agent.items())],
            stages_reached=[AgentCount(key=key, count=value) for key, value in sorted(stages.items())],
            last_run_at=last_run,
            unmapped_identity_count=self.repository.unmapped_identity_count(data_mode=filters.get("data_mode")),
            data_mode=filters.get("data_mode") or "ingested",
            reference_time=SEED_NOW,
        )

    def list_runs(self, *, page: int = 1, page_size: int = 20, **filters) -> AgentAuditRunListResponse:
        runs = self.repository.list_runs(**filters)
        page_rows, total = _paginate(runs, page, page_size)
        return AgentAuditRunListResponse(
            items=[self._to_run_summary(run) for run in page_rows],
            total=total,
            page=page,
            page_size=page_size,
            data_mode=filters.get("data_mode") or "ingested",
            reference_time=SEED_NOW,
        )

    def get_run(self, run_id: str) -> AgentAuditRunDetail:
        run = self.repository.get_run(run_id)
        if run is None or run.data_mode == MOCK_DATA_MODE:
            raise AgentAuditRunNotFoundError(run_id)
        events = self.repository.events_for_run(run.id)
        summary = self._to_run_summary(run, events)
        recs = run.recommendations
        return AgentAuditRunDetail(
            **summary.model_dump(),
            events=[self._to_event_detail(event) for event in events],
            findings=[
                LinkedFinding(
                    classification=item.classification,
                    severity_tier=item.severity_tier,
                    confidence_score=item.confidence_score,
                    operator_justification=item.operator_justification,
                    mapping_status=item.mapping_status,
                    external_cluster_id=item.external_cluster_id,
                    mapped_detection_id=item.mapped_detection_id,
                )
                for item in run.findings
            ],
            recommendation_decisions=[item.decision for item in recs],
            valve_command_sent=any(item.valve_command_sent for item in recs),
            valve_command_confirmed=any(item.valve_command_confirmed for item in recs),
            notification_sent=any(item.notification_sent for item in recs),
            safety_status=recs[0].safety_status if recs else summary.mapping_status and None,
            note="Ingested agent result. Advisory only. Agent audit logs do not replace operator history.",
        )

    def list_events(self, *, page: int = 1, page_size: int = 50, **filters) -> AgentAuditEventListResponse:
        events = self.repository.list_events(**filters)
        page_rows, total = _paginate(events, page, page_size)
        return AgentAuditEventListResponse(
            items=[self._to_event_summary(event) for event in page_rows],
            total=total,
            page=page,
            page_size=page_size,
            data_mode=filters.get("data_mode") or "ingested",
            reference_time=SEED_NOW,
        )

    def get_event(self, event_id: str) -> AgentAuditEventDetail:
        event = self.repository.get_event(event_id)
        if event is None:
            raise AgentAuditEventNotFoundError(event_id)
        return self._to_event_detail(event)
