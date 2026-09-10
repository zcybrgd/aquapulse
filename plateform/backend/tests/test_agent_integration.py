from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from app.core.exceptions import AgentIntegrationError
from app.db.models import AnomalyDetection, Asset, Incident
from app.db.models.integration import AgentFinding, AgentRun, IntegrationIdentityMapping
from app.db.session import get_session_factory
from app.integrations.clients.http_util import request_with_retry
from app.integrations.clients.investigation import HttpInvestigationAgentClient
from app.integrations.clients.response import HttpResponseAgentClient
from app.integrations.contract_check import check_agent_contract
from app.integrations.fixtures import (
    INVESTIGATION_EXAMPLE_REQUEST,
    RESPONSE_EXAMPLE_REQUEST,
    response_result_fixture,
)
from app.repositories.integrations import IdentityMappingRepository
from app.scripts.validate_agent_fixture import validate as validate_fixture
from app.services.integrations import IntegrationService

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "agents"


def _valid_investigation() -> dict:
    return json.loads((CONTRACTS / "investigation" / "v1" / "valid-response.json").read_text(encoding="utf-8"))


def _unique_investigation() -> dict:
    payload = deepcopy(_valid_investigation())
    payload["batch_id"] = f"batch-{uuid4().hex[:12]}"
    payload["investigated_threats"][0]["anomaly_id"] = str(uuid4())
    return payload


def _service() -> IntegrationService:
    return IntegrationService(get_session_factory()())


def test_existing_apis_remain_compatible(client) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    incidents = client.get("/api/incidents")
    assert incidents.status_code == 200
    detections = client.get("/api/detections")
    assert detections.status_code == 200


def test_readiness_has_no_secrets_or_urls(client) -> None:
    response = client.get("/api/integrations/agents/readiness")
    assert response.status_code == 200
    payload = response.json()
    text = json.dumps(payload).lower()
    assert payload["banner"] == "Integration prepared — agent execution disabled"
    assert payload["execution_enabled"] is False
    assert payload["safety"]["camara_enabled"] is False
    assert payload["safety"]["notifications_enabled"] is False
    assert payload["safety"]["physical_commands_enabled"] is False
    assert "groq" not in text
    assert "password" not in text
    assert "127.0.0.1" not in text
    for agent in payload["agents"]:
        assert "base_url" not in agent
        assert "url" not in agent
        assert agent["mode"] == "disabled"


def test_validate_investigation_request_and_response(client) -> None:
    request = client.post(
        "/api/integrations/agents/contracts/investigation/v1/validate-request",
        json=INVESTIGATION_EXAMPLE_REQUEST,
    )
    assert request.status_code == 200
    assert request.json()["valid"] is True
    assert request.json()["side_effects"]["incident_created"] is False

    valid = client.post(
        "/api/integrations/agents/contracts/investigation/v1/validate-response",
        json=_valid_investigation(),
    )
    assert valid.status_code == 200


def test_validate_response_agent_fixtures(client) -> None:
    request = client.post(
        "/api/integrations/agents/contracts/response/v1/validate-request",
        json=RESPONSE_EXAMPLE_REQUEST,
    )
    assert request.status_code == 200
    for name in (
        "valid-log-only.json",
        "valid-alert-and-await.json",
        "valid-autonomous-isolate.json",
        "valid-escalate-unreachable.json",
    ):
        payload = json.loads((CONTRACTS / "response" / "v1" / name).read_text(encoding="utf-8"))
        response = client.post("/api/integrations/agents/contracts/response/v1/validate-response", json=payload)
        assert response.status_code == 200, name


def test_invalid_schema_version(client) -> None:
    payload = deepcopy(INVESTIGATION_EXAMPLE_REQUEST)
    payload["schema_version"] = "2.0"
    response = client.post("/api/integrations/agents/contracts/investigation/v1/validate-request", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "agent_schema_version_unsupported"


def test_invalid_confidence_and_severity(client) -> None:
    payload = _valid_investigation()
    payload["investigated_threats"][0]["confidence_score"] = 1.5
    response = client.post("/api/integrations/agents/contracts/investigation/v1/validate-response", json=payload)
    assert response.status_code == 422

    payload = _valid_investigation()
    payload["investigated_threats"][0]["severity_tier"] = 9
    response = client.post("/api/integrations/agents/contracts/investigation/v1/validate-response", json=payload)
    assert response.status_code == 422


def test_invalid_decision_and_missing_fields(client) -> None:
    payload = response_result_fixture("LOG_ONLY")
    payload["decision"] = "EXPLODE"
    response = client.post("/api/integrations/agents/contracts/response/v1/validate-response", json=payload)
    assert response.status_code == 422

    response = client.post(
        "/api/integrations/agents/contracts/response/v1/validate-response",
        json={"schema_version": "1.0"},
    )
    assert response.status_code == 422


def test_count_mismatch(client) -> None:
    payload = _valid_investigation()
    payload["anomalies_detected_count"] = 3
    response = client.post("/api/integrations/agents/contracts/investigation/v1/validate-response", json=payload)
    assert response.status_code == 422


def test_execute_endpoints_disabled(client) -> None:
    for code in ("investigation_agent", "response_agent"):
        response = client.post(f"/api/integrations/agents/{code}/execute")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "agent_execution_disabled"
        assert "stack" not in json.dumps(response.json()).lower()


def test_unknown_ids_create_mapping_warning(test_database) -> None:
    service = _service()
    payload = _unique_investigation()
    run = service.ingest_investigation_result(payload)
    assert run.mapping_warning_count >= 1
    assert any(item.get("code") == "agent_identity_unmapped" for item in run.mapping_warnings)
    findings = service.list_findings()
    match = next(item for item in findings if item.external_anomaly_id == payload["investigated_threats"][0]["anomaly_id"])
    assert match.mapping_status == "unmapped"
    assert match.mapped_detection_id is None
    service.session.close()


def test_mapping_success_without_guessing(test_database) -> None:
    session = get_session_factory()()
    repo = IdentityMappingRepository(session)
    external_cluster = f"cluster-test-{uuid4().hex[:8]}"
    repo.upsert(
        IntegrationIdentityMapping(
            provider="investigation_agent",
            entity_type="sensor_cluster",
            external_id=external_cluster,
            internal_entity_type="detection",
            internal_public_id="DET-000001",
        )
    )
    session.commit()
    session.close()

    service = _service()
    payload = _unique_investigation()
    payload["investigated_threats"][0]["sensor_cluster_id"] = external_cluster
    run = service.ingest_investigation_result(payload)
    finding = next(
        item
        for item in service.list_findings()
        if item.external_anomaly_id == payload["investigated_threats"][0]["anomaly_id"]
    )
    assert finding.mapping_status in {"partial", "mapped"}
    assert any(item.get("code") == "agent_identity_unmapped" for item in run.mapping_warnings)
    service.session.close()


def test_idempotent_repeated_results(test_database) -> None:
    service = _service()
    payload = _unique_investigation()
    first = service.ingest_investigation_result(payload)
    second = service.ingest_investigation_result(payload)
    assert first.run_id == second.run_id
    count = service.session.scalar(select(func.count()).select_from(AgentFinding))
    again = IntegrationService(get_session_factory()())
    third = again.ingest_investigation_result(payload)
    assert third.run_id == first.run_id
    later = again.session.scalar(select(func.count()).select_from(AgentFinding))
    assert later == count
    service.session.close()
    again.session.close()


def test_ingest_does_not_mutate_incidents_detections_or_valves(test_database) -> None:
    session = get_session_factory()()
    detection = session.scalar(select(AnomalyDetection).order_by(AnomalyDetection.detection_number.asc()))
    session.close()
    if detection is None:
        from datetime import timedelta

        from app.detection.engine import DetectionEngine
        from tests.test_detections import _cleanup_detections, _ingest_scenario, _session, _unique_end

        _cleanup_detections()
        end = _unique_end()
        _ingest_scenario("SNS-HBR-007", "combined_leak_pattern", 12, end)
        engine_session = _session()
        try:
            DetectionEngine(engine_session).run(sensor_external_id="SNS-HBR-007", now=end + timedelta(seconds=30))
        finally:
            engine_session.close()

    session = get_session_factory()()
    incidents_before = session.scalar(select(func.count()).select_from(Incident))
    detections_before = session.scalar(select(func.count()).select_from(AnomalyDetection))
    detection = session.scalar(select(AnomalyDetection).order_by(AnomalyDetection.detection_number.asc()))
    assert detection is not None
    status_before = detection.status
    valve = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
    position_before = valve.current_position
    timeline_before = detection.id
    session.close()

    service = _service()
    service.ingest_investigation_result(_unique_investigation())
    service.ingest_response_result(response_result_fixture("AUTONOMOUS_ISOLATE", result_id=f"res-{uuid4().hex[:8]}"))
    service.session.close()

    session = get_session_factory()()
    assert session.scalar(select(func.count()).select_from(Incident)) == incidents_before
    assert session.scalar(select(func.count()).select_from(AnomalyDetection)) == detections_before
    detection = session.scalar(select(AnomalyDetection).where(AnomalyDetection.id == timeline_before))
    assert detection.status == status_before
    valve = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
    assert valve.current_position == position_before
    assert detection.id == timeline_before
    session.close()


def test_rejected_result_rolls_back(test_database) -> None:
    session = get_session_factory()()
    runs_before = session.scalar(select(func.count()).select_from(AgentRun))
    findings_before = session.scalar(select(func.count()).select_from(AgentFinding))
    session.close()

    service = _service()
    payload = _unique_investigation()
    payload["investigated_threats"][0]["confidence_score"] = 4
    with pytest.raises(AgentIntegrationError) as exc:
        service.ingest_investigation_result(payload)
    assert exc.value.code == "agent_result_rejected"
    service.session.close()

    session = get_session_factory()()
    assert session.scalar(select(func.count()).select_from(AgentRun)) == runs_before
    assert session.scalar(select(func.count()).select_from(AgentFinding)) == findings_before
    session.close()


def test_recommendation_valve_stays_unverified(test_database) -> None:
    service = _service()
    payload = response_result_fixture("AUTONOMOUS_ISOLATE", result_id=f"res-{uuid4().hex[:8]}")
    service.ingest_response_result(payload)
    rec = next(item for item in service.list_recommendations() if item.external_result_id == payload["result_id"])
    assert rec.decision == "AUTONOMOUS_ISOLATE"
    assert rec.safety_status == "agent_reported_unverified"
    assert rec.valve_command_verified is False
    assert rec.notification_sent is False
    service.session.close()


def test_compat_services_are_mock_and_blocked(client, test_database) -> None:
    unknown = client.get("/api/integrations/compat/v1/device-reachability/cluster-desert-042")
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "agent_identity_unmapped"

    reach = client.get("/api/integrations/compat/v1/device-reachability/SNS-HBR-007")
    assert reach.status_code == 200
    assert reach.json()["data_mode"] == "mock"

    qod = client.post("/api/integrations/compat/v1/qod/SNS-HBR-007/reserve")
    assert qod.status_code == 200
    assert qod.json()["denied"] is True
    assert qod.json()["reason"] == "camara_disabled"
    assert qod.json()["real_network_guarantee"] is False

    notify = client.post("/api/integrations/compat/v1/notify", json={"channel": "sms", "message": "demo"})
    assert notify.status_code == 200
    assert notify.json()["sent"] is False
    assert notify.json()["reason"] == "notifications_disabled"

    session = get_session_factory()()
    valve = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
    position = valve.current_position
    session.close()

    isolate = client.post("/api/integrations/compat/v1/valve/isolate", json={"device_id": "VLV-CRN-014"})
    assert isolate.status_code == 200
    assert isolate.json() == {
        "confirmed": False,
        "executed": False,
        "status": "blocked",
        "reason": "physical_commands_disabled",
        "data_mode": "mock",
    }

    session = get_session_factory()()
    valve = session.scalar(select(Asset).where(Asset.external_id == "VLV-CRN-014"))
    assert valve.current_position == position
    session.close()

    status = client.get("/api/integrations/compat/v1/valve/status/VLV-CRN-014")
    assert status.status_code == 200
    assert status.json()["aquapulse_valve_id"] == "VLV-CRN-014"
    assert status.json()["current_position"] == position


def test_http_client_timeout_and_errors() -> None:
    def timeout_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    client = HttpInvestigationAgentClient(
        base_url="http://agents.example",
        timeout_seconds=0.1,
        path="/v1/investigate",
        retries=0,
        transport=httpx.MockTransport(timeout_handler),
    )
    with pytest.raises(AgentIntegrationError) as exc:
        _await(client.health())
    assert exc.value.code == "agent_timeout"

    def bad_json(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    remote = HttpInvestigationAgentClient(
        base_url="http://agents.example",
        timeout_seconds=1,
        path="/v1/investigate",
        retries=0,
        transport=httpx.MockTransport(bad_json),
    )
    with pytest.raises(AgentIntegrationError) as err:
        _await(remote.investigate(_request_model()))
    assert err.value.code == "agent_invalid_response"

    def not_found(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "no"})

    missing = HttpResponseAgentClient(
        base_url="http://agents.example",
        timeout_seconds=1,
        path="/v1/recommend-response",
        retries=0,
        transport=httpx.MockTransport(not_found),
    )
    with pytest.raises(AgentIntegrationError) as not_found_err:
        _await(missing.recommend(_response_request_model()))
    assert not_found_err.value.code == "agent_invalid_response"

    def server_error(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    down = HttpResponseAgentClient(
        base_url="http://agents.example",
        timeout_seconds=1,
        path="/v1/recommend-response",
        retries=0,
        transport=httpx.MockTransport(server_error),
    )
    with pytest.raises(AgentIntegrationError) as down_err:
        _await(down.recommend(_response_request_model()))
    assert down_err.value.code == "agent_unreachable"


def test_missing_url_is_not_configured() -> None:
    with pytest.raises(AgentIntegrationError) as exc:
        HttpInvestigationAgentClient(base_url="", timeout_seconds=1, path="/v1/investigate", retries=0)
    assert exc.value.code == "agent_not_configured"


def test_bounded_retry_and_no_valve_retry() -> None:
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True})

    response = request_with_retry(
        "GET",
        "http://agents.example/health",
        timeout_seconds=1,
        retries=2,
        transport=httpx.MockTransport(flaky),
    )
    assert response.status_code == 200
    assert calls["n"] == 3

    valve_calls = {"n": 0}

    def always_fail(_request: httpx.Request) -> httpx.Response:
        valve_calls["n"] += 1
        return httpx.Response(500)

    failed = request_with_retry(
        "POST",
        "http://agents.example/v1/valve/isolate",
        timeout_seconds=1,
        retries=2,
        physical=True,
        transport=httpx.MockTransport(always_fail),
    )
    assert failed.status_code == 500
    assert valve_calls["n"] == 1


def test_disabled_clients_refuse_execution() -> None:
    from app.integrations.clients.investigation import DisabledInvestigationAgentClient
    from app.integrations.clients.response import DisabledResponseAgentClient

    with pytest.raises(AgentIntegrationError) as exc:
        _await(DisabledInvestigationAgentClient().investigate(_request_model()))
    assert exc.value.code == "agent_execution_disabled"
    with pytest.raises(AgentIntegrationError) as rec:
        _await(DisabledResponseAgentClient().recommend(_response_request_model()))
    assert rec.value.code == "agent_execution_disabled"


def test_contract_check_with_mocked_server() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "schema_version": "1.0"})
        if request.url.path == "/v1/contract":
            return httpx.Response(200, json={"schema_version": "1.0"})
        if request.url.path == "/v1/investigate":
            return httpx.Response(200, json=_valid_investigation())
        if request.url.path == "/v1/recommend-response":
            return httpx.Response(200, json=response_result_fixture("LOG_ONLY"))
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    investigation = check_agent_contract("investigation", "http://agents.example", transport=transport)
    assert investigation.compatible
    response = check_agent_contract("response", "http://agents.example", transport=transport)
    assert response.compatible


def test_offline_fixture_validation() -> None:
    validate_fixture("investigation", "response", _valid_investigation())
    validate_fixture("response", "response", response_result_fixture("ALERT_AND_AWAIT"))
    with pytest.raises(Exception):
        validate_fixture("investigation", "response", {"schema_version": "1.0"})


def test_list_endpoints(client) -> None:
    assert client.get("/api/integrations/agents").status_code == 200
    assert client.get("/api/integrations/agents/investigation_agent").status_code == 200
    health = client.get("/api/integrations/agents/investigation_agent/health")
    assert health.status_code == 200
    assert health.json()["status"] == "disabled"
    assert client.get("/api/integrations/agents/runs").status_code == 200
    assert client.get("/api/integrations/agents/findings").status_code == 200
    assert client.get("/api/integrations/agents/recommendations").status_code == 200
    assert client.get("/api/integrations/agents/contracts/investigation/v1").status_code == 200
    assert client.get("/api/integrations/agents/contracts/response/v1").status_code == 200


def _await(coro):
    import asyncio

    return asyncio.run(coro)


def _request_model():
    from app.integrations.contracts.investigation import InvestigationRequestV1

    return InvestigationRequestV1.model_validate(INVESTIGATION_EXAMPLE_REQUEST)


def _response_request_model():
    from app.integrations.contracts.response import ResponseRequestV1

    return ResponseRequestV1.model_validate(RESPONSE_EXAMPLE_REQUEST)
