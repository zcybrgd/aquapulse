"""Idempotent mock agent pipeline. Does not execute agents or mutate detections."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.data.incidents import SEED_NOW
from app.db.models import AgentAuditEvent
from app.db.models.detection import AnomalyDetection
from app.db.models.integration import (
    AgentFinding,
    AgentIntegration,
    AgentResponseRecommendation,
    AgentRun,
)
from app.integrations.constants import (
    CONTRACT_VERSION,
    INVESTIGATION_AGENT,
    RESPONSE_AGENT,
    SAFETY_ADVISORY,
    SAFETY_BLOCKED,
)
from app.integrations.fixtures import INVESTIGATION_EXAMPLE_BATCH, INVESTIGATION_EXAMPLE_REQUEST
from app.integrations.sanitize import sanitize_payload
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT, RESPONSE_NODES

MOCK_RUN_IDS = (
    "AGRUN-000201",
    "AGRUN-000202",
    "AGRUN-000203",
    "AGRUN-000204",
    "AGRUN-000205",
)


def _seed_network_agent(session: Session) -> AgentIntegration:
    row = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == NETWORK_AGENT_CODE))
    values = {
        "display_name": "Network Management Agent",
        "contract_version": NETWORK_CONTRACT,
        "enabled": False,
        "mode": "disabled",
        "health_status": "disabled",
        "base_url": None,
        "extra_metadata": {
            "seeded": True,
            "contract_status": "awaiting_team_confirmation",
            "note": "Network Agent contract awaiting team confirmation",
        },
    }
    if row is None:
        row = AgentIntegration(agent_code=NETWORK_AGENT_CODE, **values)
        session.add(row)
        session.flush()
        return row
    for key, value in values.items():
        setattr(row, key, value)
    session.flush()
    return row


def _clear(session: Session) -> None:
    run_ids = list(session.scalars(select(AgentRun.id).where(AgentRun.public_id.in_(MOCK_RUN_IDS))).all())
    if run_ids:
        session.execute(delete(AgentAuditEvent).where(AgentAuditEvent.agent_run_id.in_(run_ids)))
        session.execute(delete(AgentFinding).where(AgentFinding.agent_run_id.in_(run_ids)))
        session.execute(delete(AgentResponseRecommendation).where(AgentResponseRecommendation.agent_run_id.in_(run_ids)))
        session.execute(delete(AgentRun).where(AgentRun.id.in_(run_ids)))
    session.execute(delete(AgentAuditEvent).where(AgentAuditEvent.public_id.like("AAE-%")))
    session.flush()


def _run(
    session: Session,
    *,
    public_id: str,
    integration: AgentIntegration,
    agent_type: str,
    contract_version: str,
    status: str,
    source_type: str,
    source_public_id: str | None,
    request: dict[str, Any],
    response: dict[str, Any] | None,
    started_offset_min: int,
    duration_ms: int | None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> AgentRun:
    started = SEED_NOW - timedelta(minutes=started_offset_min)
    row = AgentRun(
        id=uuid4(),
        public_id=public_id,
        agent_integration_id=integration.id,
        agent_type=agent_type,
        contract_version=contract_version,
        status=status,
        correlation_id=f"corr-{public_id.lower()}",
        idempotency_key=f"mock-{public_id.lower()}",
        source_type=source_type,
        source_public_id=source_public_id,
        request_payload=sanitize_payload(request),
        response_payload=sanitize_payload(response) if response is not None else None,
        validation_errors=[],
        mapping_warnings=[],
        error_code=error_code,
        error_message=error_message,
        started_at=started,
        completed_at=started + timedelta(milliseconds=duration_ms or 0) if duration_ms is not None else None,
        duration_ms=duration_ms,
        data_mode=MOCK_DATA_MODE,
    )
    session.add(row)
    session.flush()
    return row


def _event(
    session: Session,
    *,
    public_id: str,
    run: AgentRun | None,
    agent_code: str,
    contract_version: str,
    stage: str,
    sequence: int,
    event_type: str,
    status: str,
    summary: str,
    offset_sec: int,
    node_name: str | None = None,
    incident: str | None = None,
    detection: str | None = None,
    asset: str | None = None,
    cluster: str | None = None,
    device: str | None = None,
    inputs: dict | None = None,
    outputs: dict | None = None,
    reasoning: Any = None,
    safety: Any = None,
    error_code: str | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> int:
    session.add(
        AgentAuditEvent(
            id=uuid4(),
            public_id=public_id,
            agent_run_id=run.id if run is not None else None,
            agent_code=agent_code,
            contract_version=contract_version,
            pipeline_stage=stage,
            node_name=node_name,
            sequence_number=sequence,
            event_type=event_type,
            status=status,
            incident_public_id=incident,
            detection_public_id=detection,
            asset_public_id=asset,
            external_cluster_id=cluster,
            external_device_id=device,
            summary=summary,
            input_summary=sanitize_payload(inputs or {}),
            output_summary=sanitize_payload(outputs or {}),
            reasoning_trace=sanitize_payload(reasoning if reasoning is not None else []),
            safety_checks=sanitize_payload(safety if safety is not None else []),
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            data_mode=MOCK_DATA_MODE,
            occurred_at=SEED_NOW - timedelta(seconds=offset_sec),
        )
    )
    return sequence + 1


def seed_network_audit(session: Session) -> dict[str, int]:
    _clear(session)
    investigation = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == INVESTIGATION_AGENT))
    response = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == RESPONSE_AGENT))
    network = _seed_network_agent(session)
    if investigation is None or response is None:
        raise RuntimeError("Investigation and Response agent integrations must be seeded first")

    first_detection = session.scalar(select(AnomalyDetection).order_by(AnomalyDetection.detected_at.asc()))
    detection_number = first_detection.detection_number if first_detection is not None else None

    seq = 1
    seq = _event(
        session,
        public_id=f"AAE-{seq:06d}",
        run=None,
        agent_code="lightweight_detection_model",
        contract_version="internal",
        stage="lightweight_detection",
        sequence=seq,
        event_type="candidate_flagged",
        status="completed",
        summary="Lightweight model flagged a candidate anomaly. This is screening only.",
        offset_sec=240 * 60,
        detection=detection_number,
        outputs={"screening": True, "note": "Not a confirmed pipe state."},
    )

    request = deepcopy(INVESTIGATION_EXAMPLE_REQUEST)
    request["device_msisdn"] = "+971500004821"
    request["operator_contact"] = {"phone": "+971500000000"}
    request["debug_path"] = "/home/agent/models/investigation.bin"
    request["internal_url"] = "http://127.0.0.1:9001/v1/investigate"
    batch = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    inv_run = _run(
        session,
        public_id="AGRUN-000201",
        integration=investigation,
        agent_type=INVESTIGATION_AGENT,
        contract_version=CONTRACT_VERSION,
        status="succeeded",
        source_type="batch",
        source_public_id=batch["batch_id"],
        request=request,
        response=batch,
        started_offset_min=210,
        duration_ms=5400,
    )
    seq = _event(
        session,
        public_id=f"AAE-{seq:06d}",
        run=inv_run,
        agent_code=INVESTIGATION_AGENT,
        contract_version=CONTRACT_VERSION,
        stage="anomaly_investigation",
        sequence=seq,
        event_type="run_started",
        status="started",
        summary="Investigation Agent mock import started.",
        offset_sec=210 * 60,
        node_name="ingest_batch",
        inputs=request,
        cluster="cluster-desert-042",
    )
    for threat in batch["investigated_threats"]:
        session.add(
            AgentFinding(
                provider=INVESTIGATION_AGENT,
                external_anomaly_id=threat["anomaly_id"],
                agent_run_id=inv_run.id,
                classification=threat["classification"],
                severity_tier=threat["severity_tier"],
                confidence_score=threat["confidence_score"],
                external_cluster_id=threat["sensor_cluster_id"],
                external_segment_id=threat["segment_id"],
                external_valve_id=(threat.get("criticality_metrics") or {}).get("associated_valve_id"),
                anomaly_detection_id=None,
                mapped_detection_id=None,
                mapping_status="unmapped",
                network_status=threat["network_status"],
                physical_deviations=threat["physical_deviations"],
                criticality_metrics=threat["criticality_metrics"],
                operator_justification=threat["operator_justification"],
                raw_finding=sanitize_payload(threat),
            )
        )
        seq = _event(
            session,
            public_id=f"AAE-{seq:06d}",
            run=inv_run,
            agent_code=INVESTIGATION_AGENT,
            contract_version=CONTRACT_VERSION,
            stage="anomaly_investigation",
            sequence=seq,
            event_type="finding_imported",
            status="completed",
            summary=f"Imported {threat['classification']} for {threat['sensor_cluster_id']}.",
            offset_sec=209 * 60,
            node_name="write_findings",
            cluster=threat["sensor_cluster_id"],
            device=(threat.get("criticality_metrics") or {}).get("associated_valve_id"),
            outputs=threat,
            reasoning=[{"step": "imported_team_fixture", "summary": threat["operator_justification"]}],
        )
    seq = _event(
        session,
        public_id=f"AAE-{seq:06d}",
        run=inv_run,
        agent_code=INVESTIGATION_AGENT,
        contract_version=CONTRACT_VERSION,
        stage="anomaly_investigation",
        sequence=seq,
        event_type="run_completed",
        status="completed",
        summary="Investigation Agent mock import completed. Identities remain unmapped.",
        offset_sec=208 * 60,
        duration_ms=5400,
    )

    net_run = _run(
        session,
        public_id="AGRUN-000202",
        integration=network,
        agent_type=NETWORK_AGENT_CODE,
        contract_version=NETWORK_CONTRACT,
        status="succeeded",
        source_type="draft_log",
        source_public_id="NETBATCH-000001",
        request={"note": "Network Agent contract awaiting team confirmation", "schema_version": NETWORK_CONTRACT},
        response=None,
        started_offset_min=180,
        duration_ms=1600,
    )
    network_logs = (
        ("NETEVT-000001", "connectivity_check", "completed", "cluster-desert-044", "valve-neom-north-03", "Mock connectivity verification", {"reachable": False}),
        ("NETEVT-000002", "connectivity_check", "completed", "cluster-desert-042", "valve-neom-north-01", "Mock connectivity verification", {"reachable": True}),
        ("NETEVT-000003", "qod_requested", "completed", "cluster-desert-042", "valve-neom-north-01", "Draft QoD request log", {}),
        ("NETEVT-000004", "qod_granted", "completed", "cluster-desert-042", "valve-neom-north-01", "Draft mock QoD grant", {"granted": True, "verified": False}),
        ("NETEVT-000005", "qod_denied", "completed", "cluster-desert-043", "valve-neom-north-02", "Draft mock QoD denial", {"denied": True}),
        ("NETEVT-000006", "qod_released", "completed", "cluster-desert-042", "valve-neom-north-01", "Draft mock QoD release", {}),
        ("NETEVT-000007", "agent_error", "failed", "cluster-desert-043", "valve-neom-north-02", "Mock Network Agent error", {"error": "draft_api_unavailable"}),
    )
    for index, (event_id, event_type, status, cluster, device, summary, extra) in enumerate(network_logs):
        envelope = {
            "schema_version": NETWORK_CONTRACT,
            "agent_code": NETWORK_AGENT_CODE,
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": (SEED_NOW - timedelta(minutes=175 - index)).isoformat().replace("+00:00", "Z"),
            "incident_id": None,
            "cluster_id": cluster,
            "device_id": device,
            "status": status,
            "summary": summary,
            "payload": extra,
            "data_mode": MOCK_DATA_MODE,
        }
        seq = _event(
            session,
            public_id=f"AAE-{seq:06d}",
            run=net_run,
            agent_code=NETWORK_AGENT_CODE,
            contract_version=NETWORK_CONTRACT,
            stage="network_management",
            sequence=seq,
            event_type=event_type,
            status=status,
            summary=summary,
            offset_sec=(175 - index) * 60,
            node_name=event_type,
            cluster=cluster,
            device=device,
            outputs=envelope,
        )

    def _response_run(public_id: str, decision: str, cluster: str, device: str, blocked: bool, offset: int, result_id: str) -> AgentRun:
        run = _run(
            session,
            public_id=public_id,
            integration=response,
            agent_type=RESPONSE_AGENT,
            contract_version=CONTRACT_VERSION,
            status="succeeded",
            source_type="cluster",
            source_public_id=cluster,
            request={"cluster_id": cluster, "device_id": device, "operator_contact": {"device_msisdn": "+971500004821"}},
            response={"decision": decision, "notification_sent": False, "valve_command_sent": False},
            started_offset_min=offset,
            duration_ms=2800,
        )
        session.add(
            AgentResponseRecommendation(
                provider=RESPONSE_AGENT,
                external_result_id=result_id,
                agent_run_id=run.id,
                external_incident_id=None,
                external_cluster_id=cluster,
                external_device_id=device,
                mapped_incident_number=None,
                mapped_device_id=None,
                severity_tier=3 if decision == "AUTONOMOUS_ISOLATE" else 1,
                decision=decision,
                reachability={"status": "UNREACHABLE" if decision == "ESCALATE_UNREACHABLE" else "REACHABLE"},
                notification_sent=False,
                valve_command_sent=False,
                valve_command_confirmed=False,
                human_override_requested=decision in {"ALERT_AND_AWAIT", "AUTONOMOUS_ISOLATE"},
                reasoning_trace=[{"step": "reachability_check"}, {"step": "llm_response_planner"}],
                safety_status=SAFETY_BLOCKED if blocked else SAFETY_ADVISORY,
                raw_result=sanitize_payload({"result_id": result_id, "decision": decision, "api_key": "should-redact"}),
            )
        )
        return run

    isolate = _response_run("AGRUN-000203", "AUTONOMOUS_ISOLATE", "cluster-desert-042", "valve-neom-north-01", True, 90, "mock-res-isolate-042")
    escalate = _response_run("AGRUN-000204", "ESCALATE_UNREACHABLE", "cluster-desert-044", "valve-neom-north-03", False, 70, "mock-res-escalate-044")
    alert = _response_run("AGRUN-000205", "ALERT_AND_AWAIT", "cluster-desert-044", "valve-neom-north-03", False, 50, "mock-res-alert-044")

    def _response_nodes(run: AgentRun, decision: str, cluster: str, device: str, blocked: bool, offset: int) -> None:
        nonlocal seq
        seq = _event(
            session,
            public_id=f"AAE-{seq:06d}",
            run=run,
            agent_code=RESPONSE_AGENT,
            contract_version=CONTRACT_VERSION,
            stage="response",
            sequence=seq,
            event_type="run_started",
            status="started",
            summary="Response Agent mock recommendation started.",
            offset_sec=offset * 60,
            cluster=cluster,
            device=device,
        )
        for index, node in enumerate(RESPONSE_NODES):
            seq = _event(
                session,
                public_id=f"AAE-{seq:06d}",
                run=run,
                agent_code=RESPONSE_AGENT,
                contract_version=CONTRACT_VERSION,
                stage="response",
                sequence=seq,
                event_type="node_completed",
                status="completed",
                summary=f"Response Agent node {node}.",
                offset_sec=offset * 60 - (index + 1) * 8,
                node_name=node,
                cluster=cluster,
                device=device,
                outputs={"node": node, "decision": decision, "notification_sent": False, "valve_command_sent": False},
                reasoning=[{"step": node}],
            )
        if blocked:
            seq = _event(
                session,
                public_id=f"AAE-{seq:06d}",
                run=run,
                agent_code="aquapulse_platform",
                contract_version="platform",
                stage="platform_safety",
                sequence=seq,
                event_type="safety_gate_checked",
                status="blocked",
                summary="Blocked by AquaPulse safety policy. Real execution disabled.",
                offset_sec=offset * 60 - 60,
                node_name="aquapulse_safety_gate",
                cluster=cluster,
                device=device,
                outputs={
                    "agent_requested_action": decision,
                    "verification": "unverified",
                    "real_execution": "disabled",
                    "valve_state": "unchanged",
                    "notification": "not_sent",
                    "safety_status": "blocked",
                },
                safety=[{"check": "physical_commands_disabled", "result": "blocked"}],
            )
        seq = _event(
            session,
            public_id=f"AAE-{seq:06d}",
            run=run,
            agent_code="aquapulse_platform",
            contract_version="platform",
            stage="audit",
            sequence=seq,
            event_type="audit_written",
            status="completed",
            summary="Platform audit event written. No physical command was executed.",
            offset_sec=offset * 60 - 70,
            cluster=cluster,
            device=device,
            outputs={"persisted": True, "data_mode": MOCK_DATA_MODE},
        )

    _response_nodes(isolate, "AUTONOMOUS_ISOLATE", "cluster-desert-042", "valve-neom-north-01", True, 90)
    _response_nodes(escalate, "ESCALATE_UNREACHABLE", "cluster-desert-044", "valve-neom-north-03", False, 70)
    _response_nodes(alert, "ALERT_AND_AWAIT", "cluster-desert-044", "valve-neom-north-03", False, 50)

    session.flush()
    events = int(session.scalar(select(func.count()).select_from(AgentAuditEvent).where(AgentAuditEvent.public_id.like("AAE-%"))) or 0)
    findings = int(
        session.scalar(
            select(func.count())
            .select_from(AgentFinding)
            .where(
                AgentFinding.agent_run_id.in_(
                    select(AgentRun.id).where(AgentRun.public_id.in_(MOCK_RUN_IDS))
                )
            )
        )
        or 0
    )
    return {"observations": 0, "network_events": 7, "runs": len(MOCK_RUN_IDS), "events": events, "findings": findings}
