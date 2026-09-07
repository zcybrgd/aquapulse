from copy import deepcopy

from sqlalchemy import select

from app.db.models import Asset
from app.db.models.detection import AnomalyDetection
from app.db.models.integration import AgentFinding, AgentIntegration, AgentResponseRecommendation, AgentRun
from app.db.session import get_session_factory
from app.integrations.contracts.investigation import InvestigationBatchResultV1, InvestigatedThreatV1
from app.integrations.fixtures import INVESTIGATION_EXAMPLE_BATCH
from app.integrations.sanitize import REDACTED, sanitize_payload
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT
from app.scripts.seed_database import seed_database


def test_sanitize_redacts_secrets_paths_msisdn_and_urls() -> None:
    payload = {
        "camara_api_key": "abc",
        "Authorization": "Bearer secret",
        "device_msisdn": "+971500004821",
        "operator_contact": {"phone": "+9715"},
        "nested": {"refresh_token": "t", "safe": "ok"},
        "debug_path": "/home/agent/models/weights.bin",
        "windows_path": r"C:\Users\Admin\secrets.env",
        "internal_url": "http://127.0.0.1:9001/v1/investigate",
        "base_url": "http://agent.internal",
        "visible": 12,
    }
    cleaned = sanitize_payload(payload)
    assert cleaned["camara_api_key"] == REDACTED
    assert cleaned["Authorization"] == REDACTED
    assert cleaned["device_msisdn"] == REDACTED
    assert cleaned["operator_contact"] == REDACTED
    assert cleaned["nested"]["refresh_token"] == REDACTED
    assert cleaned["nested"]["safe"] == "ok"
    assert cleaned["debug_path"] == REDACTED
    assert cleaned["windows_path"] == REDACTED
    assert cleaned["internal_url"] == REDACTED
    assert cleaned["base_url"] == REDACTED
    assert cleaned["visible"] == 12


def test_investigation_fixture_validates_and_three_findings_persist(client, test_database) -> None:
    from uuid import uuid4

    batch = InvestigationBatchResultV1.model_validate(deepcopy(INVESTIGATION_EXAMPLE_BATCH))
    assert len(batch.investigated_threats) == 3
    payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    for threat in payload["investigated_threats"]:
        threat["anomaly_id"] = str(uuid4())
    ingested = client.post("/api/integrations/agents/investigation/v1/results", json=payload)
    assert ingested.status_code == 202
    run_id = ingested.json()["run_id"]
    session = get_session_factory()()
    findings = list(
        session.scalars(
            select(AgentFinding)
            .join(AgentRun, AgentFinding.agent_run_id == AgentRun.id)
            .where(AgentRun.public_id == run_id)
        ).all()
    )
    clusters = {item.external_cluster_id for item in findings}
    assert clusters == {"cluster-desert-042", "cluster-desert-043", "cluster-desert-044"}
    session.close()


def test_findings_do_not_mutate_incidents_or_detections(client) -> None:
    incidents = client.get("/api/incidents").json()
    detections = client.get("/api/detections").json()
    assert incidents["total"] == 9
    before = {item["detection_number"]: item["status"] for item in detections["items"]}
    seed_database()
    after = {item["detection_number"]: item["status"] for item in client.get("/api/detections").json()["items"]}
    assert before == after
    valve = client.get("/api/assets/VLV-CRN-014").json()
    assert valve["current_position"] == "closed"


def test_screening_priority_label_and_awaiting_investigation(client) -> None:
    from datetime import timedelta

    from app.detection.engine import DetectionEngine
    from tests.test_detections import _cleanup_detections, _ingest_scenario, _session, _unique_end

    items = client.get("/api/detections").json()["items"]
    if not items:
        _cleanup_detections()
        end = _unique_end()
        _ingest_scenario("SNS-HBR-007", "combined_leak_pattern", 10, end)
        session = _session()
        try:
            DetectionEngine(session).run(sensor_external_id="SNS-HBR-007", now=end + timedelta(seconds=30))
        finally:
            session.close()
        items = client.get("/api/detections").json()["items"]
    assert items
    assert all(item["screening_priority_label"] == "Screening priority" for item in items)
    open_items = [item for item in items if item["status"] in {"new", "queued"}]
    assert open_items
    assert all(item["awaiting_agent_investigation"] is True for item in open_items)
    assert all(item["has_agent_finding"] is False for item in items)
    detail = client.get(f"/api/detections/{items[0]['id']}").json()
    assert detail["screening_priority_label"] == "Screening priority"
    assert detail["priority"] == items[0]["priority"]
    assert detail["agent_finding"] is None


def test_network_draft_logs_and_unconfirmed_contract(client, test_database) -> None:
    summary = client.get("/api/network-health/summary").json()
    assert "grants" not in summary
    assert "contract_status" not in summary
    assert summary["source_mode"] in {"seeded_demo", "nokia_simulator"}
    assert summary["cellular_devices"] >= 1
    assert "health score" not in summary["note"].lower()
    events = client.get("/api/network-health/events").json()
    types = {item["event_type"] for item in events["items"]}
    assert {"connectivity_check", "qod_granted", "qod_denied", "qod_released", "agent_error"} <= types
    assert all(item["data_mode"] == MOCK_DATA_MODE for item in events["items"])
    detail = client.get("/api/network-health/events/NETEVT-000004").json()
    assert detail["payload"]["schema_version"] == NETWORK_CONTRACT
    assert "input_summary" in detail
    missing = client.get("/api/network-health/events/NETEVT-MISSING")
    assert missing.status_code == 404
    session = get_session_factory()()
    row = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == NETWORK_AGENT_CODE))
    assert row is not None
    assert row.enabled is False
    assert row.mode == "disabled"
    assert row.contract_version == NETWORK_CONTRACT
    session.close()


def test_response_isolate_blocked_without_execution(client, test_database) -> None:
    from uuid import uuid4

    from app.integrations.fixtures import response_result_fixture

    payload = response_result_fixture("AUTONOMOUS_ISOLATE", result_id=f"res-{uuid4().hex[:8]}")
    ingested = client.post("/api/integrations/agents/response/v1/results", json=payload)
    assert ingested.status_code == 202
    run = client.get(f"/api/agent-audit/runs/{ingested.json()['run_id']}").json()
    assert run["decision"] == "AUTONOMOUS_ISOLATE"
    assert run["valve_command_sent"] is False
    assert run["notification_sent"] is False
    session = get_session_factory()()
    rec = session.scalar(
        select(AgentResponseRecommendation).where(
            AgentResponseRecommendation.external_result_id == payload["result_id"]
        )
    )
    assert rec is not None
    assert rec.notification_sent is False
    assert rec.valve_command_sent is False
    assert rec.safety_status == "blocked"
    session.close()


def test_audit_ordering_pagination_and_unmapped(client) -> None:
    from uuid import uuid4

    for _ in range(3):
        payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
        payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
        for threat in payload["investigated_threats"]:
            threat["anomaly_id"] = str(uuid4())
        assert client.post("/api/integrations/agents/investigation/v1/results", json=payload).status_code == 202
    page1 = client.get("/api/agent-audit/runs", params={"page": 1, "page_size": 2}).json()
    page2 = client.get("/api/agent-audit/runs", params={"page": 2, "page_size": 2}).json()
    assert page1["total"] >= 3
    assert page1["items"][0]["public_id"] != page2["items"][0]["public_id"]
    unknown = client.get("/api/agent-audit/runs/AGRUN-999999")
    assert unknown.status_code == 404


def test_imported_payloads_are_sanitized(client) -> None:
    from uuid import uuid4

    payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    for threat in payload["investigated_threats"]:
        threat["anomaly_id"] = str(uuid4())
    ingested = client.post("/api/integrations/agents/investigation/v1/results", json=payload)
    assert ingested.status_code == 202
    run = client.get(f"/api/integrations/agents/runs/{ingested.json()['run_id']}").json()
    dumped = str(run["response_payload"]) + str(run["request_payload"])
    assert "+971500004821" not in dumped


def test_no_network_decision_engine_table(test_database) -> None:
    session = get_session_factory()()
    names = session.execute(select(Asset.external_id).limit(1)).all()
    assert names
    from sqlalchemy import text

    tables = session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='network_observations'")
    ).scalar()
    assert tables is None
    session.close()


def test_seed_idempotent_and_existing_apis(client, test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.mock_agent_runs == second.mock_agent_runs == 1
    assert first.investigation_findings == second.investigation_findings == 0
    assert first.network_events == second.network_events == 7
    assert first.device_network_snapshots == second.device_network_snapshots == 9
    assert first.agent_audit_events == second.agent_audit_events
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/incidents").status_code == 200
    assert client.get("/api/assets").status_code == 200
    assert client.get("/api/analytics/overview").status_code == 200
    assert client.get("/api/integrations/agents/readiness").status_code == 200
    assert client.get("/api/integrations/agents/contracts/investigation/v1").status_code == 200
    assert client.get("/api/dashboard/summary").status_code == 200
