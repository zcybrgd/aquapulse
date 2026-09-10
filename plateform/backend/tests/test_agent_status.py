from __future__ import annotations

import asyncio
import json

import httpx

from app.api.deps import get_agent_status_checker
from app.core.config import Settings
from app.integrations.agent_status import AgentStatusChecker
from app.main import app

IA = "http://ia.test"
NA = "http://na.test"
RA = "http://ra.test"
SECRET = "super-secret-agent-token"


def _await(coro):
    return asyncio.run(coro)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "investigation_agent_url": IA,
        "network_agent_url": NA,
        "response_agent_url": RA,
        "agent_integration_enabled": False,
        "investigation_agent_enabled": False,
        "network_agent_enabled": False,
        "response_agent_enabled": False,
        "agent_health_timeout_seconds": 0.2,
        "agent_health_cache_seconds": 15,
        "nokia_network_api_key": SECRET,
    }
    values.update(overrides)
    return Settings(**values)


def _health(status: str = "ok") -> httpx.Response:
    return httpx.Response(200, json={"status": status, "service": "test"})


def _contract(version: str = "1.0") -> httpx.Response:
    return httpx.Response(200, json={"contract_version": version})


def _handler(mapping: dict[str, httpx.Response | Exception]):
    requested: list[str] = []

    def inner(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        requested.append(f"{request.method} {request.url}")
        result = mapping.get(key)
        if result is None:
            return httpx.Response(404, json={"detail": "missing"})
        if isinstance(result, Exception):
            raise result
        return result

    inner.requested = requested  # type: ignore[attr-defined]
    return inner


def _collect(settings: Settings, mapping: dict[str, httpx.Response | Exception], refresh: bool = True):
    handler = _handler(mapping)
    checker = AgentStatusChecker(settings, transport=httpx.MockTransport(handler))
    payload = _await(checker.collect(refresh=refresh))
    return payload, handler.requested  # type: ignore[attr-defined]


def _by_type(payload):
    return {agent.agent_type: agent for agent in payload.agents}


def test_all_three_agents_healthy_execution_disabled() -> None:
    payload, requested = _collect(
        _settings(),
        {
            "GET /health": _health(),
            "GET /v1/contract": _contract(),
        },
    )
    assert payload.execution_globally_enabled is False
    assert len(payload.agents) == 3
    agents = _by_type(payload)
    assert agents["investigation_agent"].health_status == "healthy"
    assert agents["investigation_agent"].reachable is True
    assert agents["investigation_agent"].execution_enabled is False
    assert agents["investigation_agent"].contract_status == "compatible"
    assert agents["investigation_agent"].contract_version == "1.0"
    assert agents["response_agent"].contract_status == "compatible"
    assert agents["network_management_agent"].health_status == "healthy"
    assert agents["network_management_agent"].contract_status == "unknown"
    assert all("investigate" not in url and "recommend-response" not in url for url in requested)


def test_all_agents_unavailable() -> None:
    payload, _ = _collect(
        _settings(),
        {
            "GET /health": httpx.ConnectError("refused"),
        },
    )
    for agent in payload.agents:
        assert agent.health_status == "unavailable"
        assert agent.reachable is False
        assert agent.error_code == "agent_unreachable"
        assert agent.error_message == "Agent did not respond."


def test_mixed_health_statuses() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "ia.test" and request.url.path == "/health":
            return _health()
        if request.url.host == "ia.test" and request.url.path == "/v1/contract":
            return _contract()
        if request.url.host == "na.test":
            raise httpx.ConnectError("refused")
        return httpx.Response(500, json={"status": "error"})

    checker = AgentStatusChecker(_settings(), transport=httpx.MockTransport(handler))
    payload = _await(checker.collect(refresh=True))
    agents = _by_type(payload)
    assert agents["investigation_agent"].health_status == "healthy"
    assert agents["network_management_agent"].health_status == "unavailable"
    assert agents["response_agent"].health_status == "unavailable"
    assert agents["response_agent"].error_code == "agent_health_invalid"


def test_missing_url() -> None:
    payload, requested = _collect(
        _settings(investigation_agent_url=""),
        {"GET /health": _health(), "GET /v1/contract": _contract()},
    )
    agent = _by_type(payload)["investigation_agent"]
    assert agent.configured is False
    assert agent.health_status == "not_configured"
    assert agent.error_code == "agent_not_configured"
    assert all("ia.test" not in url for url in requested)


def test_health_timeout() -> None:
    payload, _ = _collect(
        _settings(),
        {"GET /health": httpx.TimeoutException("slow")},
    )
    agent = _by_type(payload)["investigation_agent"]
    assert agent.health_status == "unavailable"
    assert agent.error_code == "agent_health_timeout"
    assert agent.error_message == "Agent health check timed out."


def test_invalid_health_response() -> None:
    payload, _ = _collect(
        _settings(),
        {"GET /health": httpx.Response(200, text="not-json")},
    )
    agent = _by_type(payload)["investigation_agent"]
    assert agent.health_status == "unavailable"
    assert agent.error_code == "agent_health_invalid"


def test_compatible_and_incompatible_contracts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return _health()
        if request.url.host == "ia.test":
            return _contract("1.0")
        if request.url.host == "ra.test":
            return _contract("2.0")
        return httpx.Response(404, json={"detail": "missing"})

    checker = AgentStatusChecker(_settings(), transport=httpx.MockTransport(handler))
    agents = _by_type(_await(checker.collect(refresh=True)))
    assert agents["investigation_agent"].contract_status == "compatible"
    assert agents["response_agent"].contract_status == "incompatible"
    assert agents["response_agent"].error_code == "agent_contract_mismatch"
    assert agents["response_agent"].health_status == "healthy"


def test_network_contract_stays_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return _health()
        return _contract("1.0")

    checker = AgentStatusChecker(_settings(), transport=httpx.MockTransport(handler))
    agent = _by_type(_await(checker.collect(refresh=True)))["network_management_agent"]
    assert agent.health_status == "healthy"
    assert agent.contract_status == "unknown"
    assert agent.contract_version == "1.0"


def test_feature_disabled_but_service_reachable() -> None:
    payload, _ = _collect(
        _settings(agent_integration_enabled=False, investigation_agent_enabled=True),
        {"GET /health": _health(), "GET /v1/contract": _contract()},
    )
    agent = _by_type(payload)["investigation_agent"]
    assert agent.reachable is True
    assert agent.execution_enabled is False


def test_execution_enabled_requires_master_and_agent_flags() -> None:
    payload, _ = _collect(
        _settings(
            agent_integration_enabled=True,
            investigation_agent_enabled=True,
            network_agent_enabled=False,
            response_agent_enabled=True,
        ),
        {"GET /health": _health(), "GET /v1/contract": _contract()},
    )
    agents = _by_type(payload)
    assert payload.execution_globally_enabled is True
    assert agents["investigation_agent"].execution_enabled is True
    assert agents["network_management_agent"].execution_enabled is False
    assert agents["response_agent"].execution_enabled is True


def test_failure_isolation_between_agents() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "na.test":
            raise RuntimeError(f"boom {SECRET} {NA}")
        if request.url.path == "/health":
            return _health()
        if request.url.path == "/v1/contract":
            return _contract()
        return httpx.Response(404)

    checker = AgentStatusChecker(_settings(), transport=httpx.MockTransport(handler))
    agents = _by_type(_await(checker.collect(refresh=True)))
    assert agents["investigation_agent"].health_status == "healthy"
    assert agents["response_agent"].health_status == "healthy"
    assert agents["network_management_agent"].health_status == "unavailable"
    assert agents["network_management_agent"].error_message == "Agent did not respond."


def test_urls_and_secrets_not_returned() -> None:
    payload, _ = _collect(
        _settings(),
        {"GET /health": httpx.ConnectError(f"failed to {IA} with {SECRET}")},
    )
    text = json.dumps(payload.model_dump(mode="json"))
    assert IA not in text
    assert NA not in text
    assert RA not in text
    assert SECRET not in text
    assert "127.0.0.1" not in text
    assert "http://" not in text
    assert "traceback" not in text.lower()


def test_missing_contract_endpoint_is_unknown() -> None:
    payload, _ = _collect(
        _settings(),
        {"GET /health": _health(), "GET /v1/contract": httpx.Response(404, json={"detail": "no"})},
    )
    agent = _by_type(payload)["investigation_agent"]
    assert agent.health_status == "healthy"
    assert agent.contract_status == "unknown"
    assert agent.error_code is None


def test_status_endpoint_hides_urls_and_does_not_require_execution(client) -> None:
    checker = AgentStatusChecker(
        _settings(),
        transport=httpx.MockTransport(
            _handler({"GET /health": _health(), "GET /v1/contract": _contract()})
        ),
    )
    app.dependency_overrides[get_agent_status_checker] = lambda: checker
    try:
        response = client.get("/api/integrations/status")
    finally:
        app.dependency_overrides.pop(get_agent_status_checker, None)
    assert response.status_code == 200
    body = response.json()
    text = json.dumps(body).lower()
    assert body["execution_globally_enabled"] is False
    assert len(body["agents"]) == 3
    assert "http://" not in text
    assert SECRET.lower() not in text
    assert "ia.test" not in text
    assert "investigate" not in text
    assert body["agents"][0]["execution_enabled"] is False
    assert body["agents"][0]["reachable"] is True
