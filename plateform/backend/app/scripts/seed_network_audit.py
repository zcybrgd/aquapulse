"""Clears dummy Investigation/Response agent rows. Keeps historical Network Agent drafts."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.data.incidents import SEED_NOW
from app.db.models import AgentAuditEvent
from app.db.models.integration import (
    AgentFinding,
    AgentIntegration,
    AgentResponseRecommendation,
    AgentRun,
)
from app.integrations.constants import INVESTIGATION_AGENT, RESPONSE_AGENT
from app.integrations.sanitize import sanitize_payload
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT

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
    dummy_run_ids = list(
        session.scalars(
            select(AgentRun.id).where(
                (AgentRun.public_id.in_(MOCK_RUN_IDS))
                | (
                    AgentRun.agent_type.in_((INVESTIGATION_AGENT, RESPONSE_AGENT))
                    & (AgentRun.data_mode == MOCK_DATA_MODE)
                )
            )
        ).all()
    )
    if dummy_run_ids:
        session.execute(delete(AgentAuditEvent).where(AgentAuditEvent.agent_run_id.in_(dummy_run_ids)))
        session.execute(delete(AgentFinding).where(AgentFinding.agent_run_id.in_(dummy_run_ids)))
        session.execute(delete(AgentResponseRecommendation).where(AgentResponseRecommendation.agent_run_id.in_(dummy_run_ids)))
        session.execute(delete(AgentRun).where(AgentRun.id.in_(dummy_run_ids)))
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

    seq = 1
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

    session.flush()
    events = int(session.scalar(select(func.count()).select_from(AgentAuditEvent).where(AgentAuditEvent.public_id.like("AAE-%"))) or 0)
    recommendations = int(session.scalar(select(func.count()).select_from(AgentResponseRecommendation)) or 0)
    return {
        "observations": 0,
        "network_events": 7,
        "runs": 1,
        "events": events,
        "findings": 0,
        "recommendations": recommendations,
    }
