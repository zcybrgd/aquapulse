from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import httpx

from app.core.exceptions import AgentIntegrationError
from app.data.incidents import SEED_NOW
from app.integrations.clients.http_util import raise_for_remote, request_with_retry
from app.integrations.constants import CONTRACT_VERSION, INVESTIGATION_AGENT
from app.integrations.contracts.investigation import AgentHealth, InvestigationRequestV1, InvestigationResponseV1
from app.integrations.fixtures import investigation_example_batch


class InvestigationAgentClient(Protocol):
    async def health(self) -> AgentHealth: ...

    async def investigate(self, request: InvestigationRequestV1) -> InvestigationResponseV1: ...


class DisabledInvestigationAgentClient:
    async def health(self) -> AgentHealth:
        return AgentHealth(
            agent_code=INVESTIGATION_AGENT,
            status="disabled",
            reachable=False,
            checked_at=datetime.now(timezone.utc),
            detail="Investigation Agent is disabled.",
            data_mode="mock",
        )

    async def investigate(self, request: InvestigationRequestV1) -> InvestigationResponseV1:
        _ = request
        raise AgentIntegrationError("Agent execution is disabled", code="agent_execution_disabled", status_code=503)


class MockInvestigationAgentClient:
    async def health(self) -> AgentHealth:
        return AgentHealth(
            agent_code=INVESTIGATION_AGENT,
            status="healthy",
            reachable=True,
            checked_at=datetime.now(timezone.utc),
            detail="Mock Investigation Agent.",
            data_mode="mock",
        )

    async def investigate(self, request: InvestigationRequestV1) -> InvestigationResponseV1:
        batch = investigation_example_batch()
        batch["batch_id"] = request.batch.batch_id
        batch["analysis_timestamp"] = request.requested_at.isoformat()
        return InvestigationResponseV1(
            schema_version=CONTRACT_VERSION,
            run_id=request.run_id,
            data_mode="mock",
            batch=batch,
        )


class HttpInvestigationAgentClient:
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
            raise AgentIntegrationError("Investigation Agent is not configured.", code="agent_not_configured", status_code=503)
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
        reachable = response.status_code < 500
        return AgentHealth(
            agent_code=INVESTIGATION_AGENT,
            status="healthy" if response.status_code < 400 else "unhealthy",
            reachable=reachable,
            checked_at=datetime.now(timezone.utc),
            data_mode="remote",
        )

    async def investigate(self, request: InvestigationRequestV1) -> InvestigationResponseV1:
        response = request_with_retry(
            "POST",
            f"{self.base_url}{self.path}",
            timeout_seconds=self.timeout_seconds,
            retries=self.retries,
            json=request.model_dump(mode="json"),
            transport=self.transport,
        )
        payload = raise_for_remote(response)
        if payload.get("schema_version") not in (None, CONTRACT_VERSION, "1.0"):
            raise AgentIntegrationError(
                "Unsupported agent schema version.",
                code="agent_schema_version_unsupported",
                status_code=422,
            )
        if "batch" not in payload and "investigated_threats" in payload:
            payload = {"schema_version": CONTRACT_VERSION, "run_id": request.run_id, "batch": payload}
        try:
            return InvestigationResponseV1.model_validate(payload)
        except Exception as exc:
            raise AgentIntegrationError(
                "The agent response did not match contract 1.0.",
                code="agent_contract_mismatch",
                status_code=422,
            ) from exc
