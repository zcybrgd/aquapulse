from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import AgentAuditEvent
from app.db.models.integration import AgentFinding, AgentResponseRecommendation, AgentRun
from app.db.session import get_session_factory
from app.integrations.fixtures import INVESTIGATION_EXAMPLE_BATCH, response_result_fixture
from app.network.constants import MOCK_DATA_MODE
from app.scripts.cleanup_dummy_agent_data import (
    delete_dummy_agent_data,
    preview_dummy_agent_data,
    refuse_production,
    table_totals,
)
from app.scripts.seed_database import seed_database


def _counts(session):
    return {
        "runs": int(session.scalar(select(func.count()).select_from(AgentRun)) or 0),
        "findings": int(session.scalar(select(func.count()).select_from(AgentFinding)) or 0),
        "recommendations": int(session.scalar(select(func.count()).select_from(AgentResponseRecommendation)) or 0),
        "events": int(session.scalar(select(func.count()).select_from(AgentAuditEvent)) or 0),
        "mock_runs": int(session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.data_mode == MOCK_DATA_MODE)) or 0),
        "mock_events": int(session.scalar(select(func.count()).select_from(AgentAuditEvent).where(AgentAuditEvent.data_mode == MOCK_DATA_MODE)) or 0),
    }


def test_seed_creates_zero_dummy_agent_operational_rows(test_database) -> None:
    first = seed_database()
    second = seed_database()
    session = get_session_factory()()
    counts = _counts(session)
    remaining = preview_dummy_agent_data(session)
    session.close()
    assert first.mock_agent_runs == second.mock_agent_runs == 0
    assert first.investigation_findings == second.investigation_findings == 0
    assert first.network_events == second.network_events == 0
    assert counts["mock_runs"] == 0
    assert counts["mock_events"] == 0
    assert remaining.agent_runs == 0
    assert remaining.agent_findings == 0
    assert remaining.agent_response_recommendations == 0
    assert remaining.agent_audit_events == 0
    assert remaining.mock_network_agent_events == 0


def test_agent_pages_are_empty_until_ingest(client, test_database) -> None:
    seed_database()
    findings = client.get("/api/integrations/agents/findings").json()
    recommendations = client.get("/api/integrations/agents/recommendations").json()
    assert findings == []
    assert recommendations == []
    assert client.get("/api/network-health/events").json()["total"] == 0
    assert client.get("/api/agent-audit/runs").json()["total"] == 0
    dashboard = client.get("/api/dashboard/summary").json()
    assert dashboard["average_response_time_min"] is None
    assert dashboard["estimated_water_loss_m3"] is None
    incident = client.get("/api/incidents/INC-1842").json()
    assert incident["agent_investigation_summary"] == "Awaiting Investigation Agent result"
    assert incident["device_reachability"] == "Unavailable"
    assert incident["network_priority_status"] == "Unavailable"
    text = str(findings) + str(recommendations)
    assert "cluster-desert" not in text
    assert "seg-neom" not in text
    assert "valve-neom" not in text


def test_cleanup_dry_run_does_not_delete(client, test_database) -> None:
    payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    for threat in payload["investigated_threats"]:
        threat["anomaly_id"] = str(uuid4())
    assert client.post("/api/integrations/agents/investigation/v1/results", json=payload).status_code == 202
    session = get_session_factory()()
    before = table_totals(session)
    selected = preview_dummy_agent_data(session)
    after = table_totals(session)
    session.close()
    assert selected.agent_findings >= 3
    assert after.agent_findings == before.agent_findings
    assert after.agent_runs == before.agent_runs


def test_cleanup_confirm_removes_demo_ids(client, test_database) -> None:
    payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    for threat in payload["investigated_threats"]:
        threat["anomaly_id"] = str(uuid4())
    assert client.post("/api/integrations/agents/investigation/v1/results", json=payload).status_code == 202
    session = get_session_factory()()
    try:
        deleted = delete_dummy_agent_data(session)
        session.commit()
        remaining = preview_dummy_agent_data(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    assert deleted.agent_findings >= 3
    assert remaining.agent_runs == 0
    assert remaining.agent_findings == 0
    leftover = client.get("/api/integrations/agents/findings").json()
    assert "cluster-desert" not in str(leftover)
    assert "seg-neom" not in str(leftover)
    assert "valve-neom" not in str(leftover)


def test_refuse_production() -> None:
    with pytest.raises(SystemExit):
        refuse_production(Settings(app_env="production"))


def test_mocked_investigation_ingest_preserves_confidence(client, test_database) -> None:
    payload = deepcopy(INVESTIGATION_EXAMPLE_BATCH)
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    expected = {}
    for threat in payload["investigated_threats"]:
        threat["anomaly_id"] = str(uuid4())
        expected[threat["anomaly_id"]] = threat["confidence_score"]
    ingested = client.post("/api/integrations/agents/investigation/v1/results", json=payload)
    assert ingested.status_code == 202
    findings = client.get("/api/integrations/agents/findings").json()
    stored = {item["external_anomaly_id"]: item["confidence_score"] for item in findings if item["external_anomaly_id"] in expected}
    assert stored == expected
    assert all(item["mapped_detection_id"] is None for item in findings if item["external_anomaly_id"] in expected)


def test_mocked_response_ingest_preserves_supplied_data_mode(client, test_database) -> None:
    response = response_result_fixture("ALERT_AND_AWAIT", result_id=f"res-{uuid4().hex[:8]}")
    response["data_mode"] = "simulated"
    posted = client.post("/api/integrations/agents/response/v1/results", json=response)
    assert posted.status_code == 202
    recs = client.get("/api/integrations/agents/recommendations").json()
    stored = next(item for item in recs if item["external_result_id"] == response["result_id"])
    assert stored["decision"] == "ALERT_AND_AWAIT"
    assert stored["data_mode"] == "simulated"
    assert stored["valve_command_sent"] is False


def test_execute_endpoints_remain_disabled(client) -> None:
    refused = client.post("/api/integrations/agents/investigation_agent/execute")
    assert refused.status_code == 503
    response = client.post("/api/integrations/agents/response_agent/execute")
    assert response.status_code == 503
