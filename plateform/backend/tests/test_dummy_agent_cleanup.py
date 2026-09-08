from copy import deepcopy
from uuid import uuid4

from sqlalchemy import func, select

from app.db.models import AgentAuditEvent
from app.db.models.integration import AgentFinding, AgentResponseRecommendation, AgentRun
from app.db.session import get_session_factory
from app.integrations.fixtures import INVESTIGATION_EXAMPLE_BATCH, response_result_fixture
from app.network.constants import MOCK_DATA_MODE
from app.scripts.seed_database import seed_database


def _counts(session):
    return {
        "mock_runs": int(session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.data_mode == MOCK_DATA_MODE)) or 0),
        "mock_events": int(session.scalar(select(func.count()).select_from(AgentAuditEvent).where(AgentAuditEvent.data_mode == MOCK_DATA_MODE)) or 0),
        "findings": int(session.scalar(select(func.count()).select_from(AgentFinding)) or 0),
        "recommendations": int(session.scalar(select(func.count()).select_from(AgentResponseRecommendation)) or 0),
    }


def test_seed_creates_zero_dummy_agent_operational_rows(test_database) -> None:
    summary = seed_database()
    session = get_session_factory()()
    counts = _counts(session)
    session.close()
    assert summary.mock_agent_runs == 0
    assert summary.investigation_findings == 0
    assert summary.network_events == 0
    assert counts["mock_runs"] == 0
    assert counts["mock_events"] == 0


def test_agent_pages_are_empty_until_ingest(client, test_database) -> None:
    seed_database()
    findings = client.get("/api/integrations/agents/findings").json()
    recommendations = client.get("/api/integrations/agents/recommendations").json()
    assert all(item.get("data_mode") != MOCK_DATA_MODE for item in findings)
    assert all(item.get("data_mode") != MOCK_DATA_MODE for item in recommendations)
    assert client.get("/api/network-health/events").json()["total"] == 0
    dashboard = client.get("/api/dashboard/summary").json()
    assert dashboard["average_response_time_min"] is None
    assert dashboard["estimated_water_loss_m3"] is None
    incident = client.get("/api/incidents/INC-1842").json()
    assert incident["agent_investigation_summary"] == "Awaiting Investigation Agent result"
    assert incident["device_reachability"] == "Unavailable"
    assert incident["network_priority_status"] == "Unavailable"


def test_real_contract_fixtures_still_persist_and_unknown_ids_stay_unmapped(client, test_database) -> None:
    payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    for threat in payload["investigated_threats"]:
        threat["anomaly_id"] = str(uuid4())
    ingested = client.post("/api/integrations/agents/investigation/v1/results", json=payload)
    assert ingested.status_code == 202
    run_id = ingested.json()["run_id"]
    findings = [item for item in client.get("/api/integrations/agents/findings").json() if item["run_id"] == run_id]
    assert len(findings) == 3
    detail = client.get(f"/api/integrations/agents/findings/{findings[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == findings[0]["id"]
    assert detail.json()["external_anomaly_id"] == findings[0]["external_anomaly_id"]
    assert all(item["mapped_detection_id"] is None for item in findings)
    assert all(item["data_mode"] != MOCK_DATA_MODE for item in findings)

    response = response_result_fixture("AUTONOMOUS_ISOLATE", result_id=f"res-{uuid4().hex[:8]}")
    posted = client.post("/api/integrations/agents/response/v1/results", json=response)
    assert posted.status_code == 202
    recs = client.get("/api/integrations/agents/recommendations").json()
    isolate = next(item for item in recs if item["external_result_id"] == response["result_id"])
    assert isolate["decision"] == "AUTONOMOUS_ISOLATE"
    assert isolate["safety_status"] == "agent_reported_unverified"
    assert isolate["valve_command_sent"] is False


def test_execute_endpoints_remain_disabled(client) -> None:
    refused = client.post("/api/integrations/agents/investigation_agent/execute")
    assert refused.status_code == 503
    response = client.post("/api/integrations/agents/response_agent/execute")
    assert response.status_code == 503
