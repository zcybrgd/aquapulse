from __future__ import annotations

import time

import httpx

from app.core.exceptions import AgentIntegrationError


def request_with_retry(
    method: str,
    url: str,
    *,
    timeout_seconds: float,
    retries: int,
    physical: bool = False,
    json: dict | None = None,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Response:
    """Bounded retries for advisory HTTP only. Never retry physical-command requests."""
    attempts = 1 if physical else max(1, retries + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
                response = client.request(method, url, json=json)
            if response.status_code >= 500 and attempt < attempts - 1 and not physical:
                time.sleep(0.05 * (attempt + 1))
                continue
            return response
        except httpx.TimeoutException as exc:
            last_error = exc
            if physical or attempt >= attempts - 1:
                raise AgentIntegrationError("The agent did not respond in time.", code="agent_timeout", status_code=504) from exc
            time.sleep(0.05 * (attempt + 1))
        except httpx.RequestError as exc:
            last_error = exc
            if physical or attempt >= attempts - 1:
                raise AgentIntegrationError("The agent could not be reached.", code="agent_unreachable", status_code=503) from exc
            time.sleep(0.05 * (attempt + 1))
    raise AgentIntegrationError("The agent could not be reached.", code="agent_unreachable", status_code=503) from last_error


def raise_for_remote(response: httpx.Response) -> dict:
    if response.status_code >= 400:
        code = "agent_invalid_response" if response.status_code < 500 else "agent_unreachable"
        raise AgentIntegrationError(
            "The agent returned an error response.",
            code=code,
            status_code=502,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise AgentIntegrationError("The agent returned malformed JSON.", code="agent_invalid_response", status_code=502) from exc
    if not isinstance(payload, dict):
        raise AgentIntegrationError("The agent returned malformed JSON.", code="agent_invalid_response", status_code=502)
    return payload
