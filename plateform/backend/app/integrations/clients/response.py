from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import httpx

from app.core.exceptions import AgentIntegrationError
from app.integrations.clients.http_util import raise_for_remote, request_with_retry
from app.integrations.constants import CONTRACT_VERSION, RESPONSE_AGENT
from app.integrations.contracts.investigation import AgentHealth
from app.integrations.contracts.response import ResponseRequestV1, ResponseResultV1
from app.integrations.fixtures import response_result_fixture


class ResponseAgentClient(Protocol):
    async def health(self) -> AgentHealth: ...

    async def recommend(self, request: ResponseRequestV1) -> ResponseResultV1: ...


class DisabledResponseAgentClient:
    async def health(self) -> AgentHealth:
        return AgentHealth(
            agent_code=RESPONSE_AGENT,
            status="disabled",
            reachable=False,
            checked_at=datetime.now(timezone.utc),
            detail="Response Agent is disabled.",
            data_mode="mock",
        )

    async def recommend(self, request: ResponseRequestV1) -> ResponseResultV1:
        _ = request
        raise AgentIntegrationError("Agent execution is disabled", code="agent_execution_disabled", status_code=503)


class MockResponseAgentClient:
    async def health(self) -> AgentHealth:
        return AgentHealth(
            agent_code=RESPONSE_AGENT,
            status="healthy",
            reachable=True,
            checked_at=datetime.now(timezone.utc),
            detail="Mock Response Agent.",
            data_mode="mock",
        )

    async def recommend(self, request: ResponseRequestV1) -> ResponseResultV1:
        payload = response_result_fixture("ALERT_AND_AWAIT", result_id=f"mock-{request.run_id}")
        payload["incident_id"] = request.incident_id
        payload["cluster_id"] = request.cluster_id
        payload["device_id"] = request.device_id
        payload["severity_tier"] = request.severity_tier
        payload["valve_command_sent"] = False
        payload["valve_command_confirmed"] = False
        payload["notification_sent"] = False
        return ResponseResultV1.model_validate(payload)


class HttpResponseAgentClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        path: str,
        retries: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise AgentIntegrationError("Response Agent is not configured.", code="agent_not_configured", status_code=503)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.path = path if path.startswith("/") else f"/{path}"
        self.retries = retries
        self.transport = transport

    async def health(self) -> AgentHealth:
        response = request_with_retry(
            "GET",
            f"{self.base_url}/health",
            timeout_seconds=self.timeout_seconds,
            retries=self.retries,
            transport=self.transport,
        )
        return AgentHealth(
            agent_code=RESPONSE_AGENT,
            status="healthy" if response.status_code < 400 else "unhealthy",
            reachable=response.status_code < 500,
            checked_at=datetime.now(timezone.utc),
            data_mode="remote",
        )

    async def recommend(self, request: ResponseRequestV1) -> ResponseResultV1:
        response = request_with_retry(
            "POST",
            f"{self.base_url}{self.path}",
            timeout_seconds=self.timeout_seconds,
            retries=self.retries,
            json=request.model_dump(mode="json"),
            transport=self.transport,
        )
        payload = raise_for_remote(response)
        version = payload.get("schema_version")
        if version not in (None, CONTRACT_VERSION, "1.0"):
            raise AgentIntegrationError(
                "Unsupported agent schema version.",
                code="agent_schema_version_unsupported",
                status_code=422,
            )
        try:
            return ResponseResultV1.model_validate(payload)
        except Exception as exc:
            raise AgentIntegrationError(
                "The agent response did not match contract 1.0.",
                code="agent_contract_mismatch",
                status_code=422,
            ) from exc
