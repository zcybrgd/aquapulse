"""Read-only agent readiness probes. Never execute an agent."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.integrations.constants import CONTRACT_VERSION, INVESTIGATION_AGENT, RESPONSE_AGENT
from app.network.constants import NETWORK_AGENT_CODE
from app.schemas.integrations import AgentRuntimeStatus, IntegrationStatusResponse

HEALTHY_STATUS_VALUES = {"ok", "healthy", "up", "ready"}
ERROR_MESSAGES = {
    "agent_not_configured": "Agent URL is not configured.",
    "agent_unreachable": "Agent did not respond.",
    "agent_health_timeout": "Agent health check timed out.",
    "agent_health_invalid": "Agent health response was invalid.",
    "agent_contract_unavailable": "Agent contract endpoint is not available.",
    "agent_contract_mismatch": "Agent contract version is incompatible.",
}


@dataclass(frozen=True)
class AgentProbeSpec:
    agent_type: str
    display_name: str
    base_url: str
    health_path: str
    contract_path: str
    expected_contract_version: str
    execution_enabled: bool
    claim_contract_compatibility: bool


@dataclass
class _CacheEntry:
    status: AgentRuntimeStatus
    expires_at: float


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _safe_message(code: str) -> str:
    return ERROR_MESSAGES[code]


def _status(
    spec: AgentProbeSpec,
    *,
    configured: bool,
    reachable: bool,
    health_status: str,
    contract_status: str,
    contract_version: str | None = None,
    checked_at: datetime,
    response_time_ms: int | None = None,
    error_code: str | None = None,
) -> AgentRuntimeStatus:
    return AgentRuntimeStatus(
        agent_type=spec.agent_type,  # type: ignore[arg-type]
        display_name=spec.display_name,
        configured=configured,
        execution_enabled=spec.execution_enabled,
        reachable=reachable,
        health_status=health_status,  # type: ignore[arg-type]
        contract_status=contract_status,  # type: ignore[arg-type]
        contract_version=contract_version,
        checked_at=checked_at,
        response_time_ms=response_time_ms,
        error_code=error_code,  # type: ignore[arg-type]
        error_message=_safe_message(error_code) if error_code else None,
    )


def build_agent_specs(settings: Settings) -> tuple[AgentProbeSpec, ...]:
    master = settings.agent_integration_enabled
    return (
        AgentProbeSpec(
            agent_type=INVESTIGATION_AGENT,
            display_name="Investigation Agent",
            base_url=settings.investigation_agent_url.strip(),
            health_path=settings.investigation_agent_health_path or "/health",
            contract_path=settings.investigation_agent_contract_path or "/v1/contract",
            expected_contract_version=settings.investigation_agent_contract_version or CONTRACT_VERSION,
            execution_enabled=bool(master and settings.investigation_agent_enabled),
            claim_contract_compatibility=True,
        ),
        AgentProbeSpec(
            agent_type=NETWORK_AGENT_CODE,
            display_name="Network Agent",
            base_url=settings.network_agent_url.strip(),
            health_path=settings.network_agent_health_path or "/health",
            contract_path=settings.network_agent_contract_path or "/v1/contract",
            expected_contract_version="",
            execution_enabled=bool(master and settings.network_agent_enabled),
            claim_contract_compatibility=False,
        ),
        AgentProbeSpec(
            agent_type=RESPONSE_AGENT,
            display_name="Response Agent",
            base_url=settings.response_agent_url.strip(),
            health_path=settings.response_agent_health_path or "/health",
            contract_path=settings.response_agent_contract_path or "/v1/contract",
            expected_contract_version=settings.response_agent_contract_version or CONTRACT_VERSION,
            execution_enabled=bool(master and settings.response_agent_enabled),
            claim_contract_compatibility=True,
        ),
    )


def _health_payload_ok(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    if "status" not in body:
        return True
    status = str(body.get("status") or "").strip().lower()
    return status in HEALTHY_STATUS_VALUES


def _contract_version(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    for key in ("contract_version", "schema_version", "version"):
        value = body.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[httpx.Response | None, Any | None, str | None]:
    try:
        response = await client.get(url)
    except httpx.TimeoutException:
        return None, None, "agent_health_timeout"
    except httpx.RequestError:
        return None, None, "agent_unreachable"
    try:
        body = response.json()
    except ValueError:
        body = None
    return response, body, None


async def probe_agent(spec: AgentProbeSpec, client: httpx.AsyncClient) -> AgentRuntimeStatus:
    checked_at = _utc_now()
    if not spec.base_url:
        return _status(
            spec,
            configured=False,
            reachable=False,
            health_status="not_configured",
            contract_status="unknown",
            checked_at=checked_at,
            error_code="agent_not_configured",
        )

    started = time.perf_counter()
    health_response, health_body, health_error = await _get_json(client, _join_url(spec.base_url, spec.health_path))
    response_time_ms = max(0, int((time.perf_counter() - started) * 1000))

    if health_error == "agent_health_timeout":
        return _status(
            spec,
            configured=True,
            reachable=False,
            health_status="unavailable",
            contract_status="unavailable",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error_code="agent_health_timeout",
        )
    if health_error or health_response is None:
        return _status(
            spec,
            configured=True,
            reachable=False,
            health_status="unavailable",
            contract_status="unavailable",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error_code="agent_unreachable",
        )
    if health_response.status_code >= 400 or not _health_payload_ok(health_body):
        return _status(
            spec,
            configured=True,
            reachable=False,
            health_status="unavailable",
            contract_status="unavailable",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error_code="agent_health_invalid",
        )

    contract_response, contract_body, contract_error = await _get_json(
        client, _join_url(spec.base_url, spec.contract_path)
    )
    if contract_error or contract_response is None:
        return _status(
            spec,
            configured=True,
            reachable=True,
            health_status="healthy",
            contract_status="unknown",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error_code="agent_contract_unavailable" if contract_error == "agent_health_timeout" else None,
        )

    if contract_response.status_code == 404:
        return _status(
            spec,
            configured=True,
            reachable=True,
            health_status="healthy",
            contract_status="unknown",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
        )

    if contract_response.status_code >= 400 or contract_body is None:
        return _status(
            spec,
            configured=True,
            reachable=True,
            health_status="healthy",
            contract_status="unavailable",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error_code="agent_contract_unavailable",
        )

    version = _contract_version(contract_body)
    if not spec.claim_contract_compatibility:
        return _status(
            spec,
            configured=True,
            reachable=True,
            health_status="healthy",
            contract_status="unknown",
            contract_version=version,
            checked_at=checked_at,
            response_time_ms=response_time_ms,
        )

    if version is None:
        return _status(
            spec,
            configured=True,
            reachable=True,
            health_status="healthy",
            contract_status="unknown",
            checked_at=checked_at,
            response_time_ms=response_time_ms,
        )

    if version != spec.expected_contract_version:
        return _status(
            spec,
            configured=True,
            reachable=True,
            health_status="healthy",
            contract_status="incompatible",
            contract_version=version,
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error_code="agent_contract_mismatch",
        )

    return _status(
        spec,
        configured=True,
        reachable=True,
        health_status="healthy",
        contract_status="compatible",
        contract_version=version,
        checked_at=checked_at,
        response_time_ms=response_time_ms,
    )


async def _safe_probe(spec: AgentProbeSpec, client: httpx.AsyncClient) -> AgentRuntimeStatus:
    try:
        return await probe_agent(spec, client)
    except Exception:
        return _status(
            spec,
            configured=bool(spec.base_url),
            reachable=False,
            health_status="unavailable" if spec.base_url else "not_configured",
            contract_status="unavailable" if spec.base_url else "unknown",
            checked_at=_utc_now(),
            error_code="agent_unreachable" if spec.base_url else "agent_not_configured",
        )


class AgentStatusChecker:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport
        self._cache: dict[str, _CacheEntry] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    async def collect(self, *, refresh: bool = False) -> IntegrationStatusResponse:
        specs = build_agent_specs(self.settings)
        timeout = max(0.1, float(self.settings.agent_health_timeout_seconds))
        cache_seconds = max(0, int(self.settings.agent_health_cache_seconds))
        now = time.monotonic()

        pending: list[AgentProbeSpec] = []
        results: dict[str, AgentRuntimeStatus] = {}
        for spec in specs:
            cached = self._cache.get(spec.agent_type)
            if not refresh and cached and cached.expires_at > now:
                results[spec.agent_type] = cached.status
            else:
                pending.append(spec)

        if pending:
            client_kwargs: dict[str, Any] = {
                "timeout": httpx.Timeout(timeout, connect=timeout),
                "follow_redirects": False,
            }
            if self.transport is not None:
                client_kwargs["transport"] = self.transport
            async with httpx.AsyncClient(**client_kwargs) as client:
                probed = await asyncio.gather(*[_safe_probe(spec, client) for spec in pending])
            expires_at = time.monotonic() + cache_seconds
            for spec, status in zip(pending, probed, strict=True):
                results[spec.agent_type] = status
                if cache_seconds > 0:
                    self._cache[spec.agent_type] = _CacheEntry(status=status, expires_at=expires_at)

        return IntegrationStatusResponse(
            generated_at=_utc_now(),
            execution_globally_enabled=bool(self.settings.agent_integration_enabled),
            agents=[results[spec.agent_type] for spec in specs],
        )


_default_checker: AgentStatusChecker | None = None


def get_agent_status_checker() -> AgentStatusChecker:
    global _default_checker
    if _default_checker is None:
        _default_checker = AgentStatusChecker(get_settings())
    return _default_checker


def reset_agent_status_checker() -> None:
    global _default_checker
    _default_checker = None
