"""Provider-independent Nokia/CAMARA adapters.

Browser code never calls these. Routes must depend on DeviceNetworkProvider
through factory injection — not RapidAPI details.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.core.exceptions import DeviceNetworkProviderError
from app.db.base import utc_now
from app.network.device_network import (
    DeviceNetworkProvider,
    LocationResult,
    ReachabilityResult,
    SourceMode,
    configured_source_mode,
    normalize_location_payload,
    normalize_reachability_payload,
)

logger = logging.getLogger(__name__)


class DisabledDeviceNetworkProvider:
    provider_name = "disabled"
    source_mode: SourceMode = "seeded_demo"

    async def get_reachability(self, device_msisdn: str) -> ReachabilityResult:
        _ = device_msisdn
        return ReachabilityResult(
            status="not_checked",
            error_code="provider_disabled",
            error_message="Nokia Network as Code is disabled in this environment.",
            raw={"status": "disabled"},
        )

    async def retrieve_location(self, device_msisdn: str) -> LocationResult:
        _ = device_msisdn
        return LocationResult(
            error_code="provider_disabled",
            error_message="Nokia Network as Code is disabled in this environment.",
            raw={"status": "disabled"},
        )


class MockNokiaDeviceNetworkProvider:
    """Deterministic demonstration / simulator responses. Never calls the internet."""

    def __init__(self, source_mode: SourceMode = "seeded_demo") -> None:
        self.provider_name = "nokia_mock"
        self.source_mode = source_mode

    def _profile(self, device_msisdn: str) -> str:
        digits = "".join(ch for ch in device_msisdn if ch.isdigit())
        return digits[-4:] if len(digits) >= 4 else digits

    async def get_reachability(self, device_msisdn: str) -> ReachabilityResult:
        profile = self._profile(device_msisdn)
        now = utc_now().isoformat()
        if profile in {"7007"}:
            payload = {"reachable": False, "connectivity": [], "lastStatusTime": now}
        elif profile in {"0221"}:
            payload = {"lastStatusTime": now}
        elif profile in {"0601"}:
            raise DeviceNetworkProviderError(
                "Nokia simulator rejected the reachability request.",
                code="nokia_simulator_error",
            )
        elif profile in {"0201"}:
            payload = {"reachable": True, "connectivity": ["SMS"], "lastStatusTime": now}
        else:
            payload = {"reachable": True, "connectivity": ["DATA"], "lastStatusTime": now}
        return normalize_reachability_payload(payload)

    async def retrieve_location(self, device_msisdn: str) -> LocationResult:
        profile = self._profile(device_msisdn)
        now = utc_now().isoformat()
        if profile in {"7007", "0401"}:
            return LocationResult(raw={"reason": "location_unavailable"}, error_code="location_unavailable")
        if profile in {"0601"}:
            raise DeviceNetworkProviderError(
                "Nokia simulator rejected the location request.",
                code="nokia_simulator_error",
            )
        # Offsets are network-cell observations, not GPS.
        offsets = {
            "4821": (25.0894, 55.1402, 420.0),
            "0201": (24.4768, 54.3704, 780.0),
            "0221": (24.2271, 55.7658, 1100.0),
            "0044": (25.4178, 51.5009, 850.0),
            "0502": (25.4182, 51.5014, 850.0),
            "0301": (24.2264, 55.7651, 960.0),
        }
        latitude, longitude, radius = offsets.get(profile, (25.2048, 55.2708, 1500.0))
        payload = {
            "lastLocationTime": now,
            "area": {
                "areaType": "CIRCLE",
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius,
            },
        }
        return normalize_location_payload(payload)


class HttpNokiaDeviceNetworkProvider:
    """Live Nokia Network as Code / CAMARA HTTP adapter. Tests inject transport."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.provider_name = "nokia_camara"
        self.source_mode: SourceMode = "nokia_live"
        self._settings = settings
        self._transport = transport
        self._timeout = settings.nokia_network_timeout_seconds
        self._retries = max(0, settings.nokia_network_max_retries)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._settings.nokia_network_api_key:
            headers["X-RapidAPI-Key"] = self._settings.nokia_network_api_key
        if self._settings.nokia_network_api_host:
            headers["X-RapidAPI-Host"] = self._settings.nokia_network_api_host
        return headers

    def _url(self, path: str) -> str:
        base = self._settings.nokia_network_api_base_url.rstrip("/") + "/"
        return urljoin(base, path.lstrip("/"))

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = self._url(path)
        last_error: Exception | None = None
        attempts = self._retries + 1
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                    response = await client.post(url, json=body, headers=self._headers())
                if response.status_code >= 500 and attempt < attempts - 1:
                    await asyncio.sleep(0.05 * (attempt + 1))
                    continue
                if response.status_code >= 400:
                    raise DeviceNetworkProviderError(
                        "Nokia Network as Code returned an error response.",
                        code="nokia_http_error",
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise DeviceNetworkProviderError(
                        "Nokia Network as Code returned malformed JSON.",
                        code="nokia_malformed_response",
                    ) from exc
                if not isinstance(payload, dict):
                    raise DeviceNetworkProviderError(
                        "Nokia Network as Code returned malformed JSON.",
                        code="nokia_malformed_response",
                    )
                return payload
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise DeviceNetworkProviderError(
                        "Nokia Network as Code did not respond in time.",
                        code="nokia_timeout",
                    ) from exc
                await asyncio.sleep(0.05 * (attempt + 1))
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise DeviceNetworkProviderError(
                        "Nokia Network as Code could not be reached.",
                        code="nokia_unreachable",
                    ) from exc
                await asyncio.sleep(0.05 * (attempt + 1))
        raise DeviceNetworkProviderError(
            "Nokia Network as Code could not be reached.",
            code="nokia_unreachable",
        ) from last_error

    async def get_reachability(self, device_msisdn: str) -> ReachabilityResult:
        payload = await self._post(
            self._settings.nokia_reachability_path,
            {"device": {"phoneNumber": device_msisdn}},
        )
        return normalize_reachability_payload(payload)

    async def retrieve_location(self, device_msisdn: str) -> LocationResult:
        payload = await self._post(
            self._settings.nokia_location_path,
            {"device": {"phoneNumber": device_msisdn}, "maxAge": 120},
        )
        return normalize_location_payload(payload)


def build_device_network_provider(
    settings: Settings,
    transport: httpx.BaseTransport | None = None,
) -> DeviceNetworkProvider:
    mode = (settings.nokia_network_api_mode or "mock").strip().lower()
    if mode == "disabled" or (not settings.nokia_network_api_enabled and mode == "disabled"):
        return DisabledDeviceNetworkProvider()
    if settings.nokia_network_api_enabled and mode == "live":
        if settings.nokia_network_api_base_url.strip() and settings.nokia_network_api_key.strip():
            return HttpNokiaDeviceNetworkProvider(settings, transport=transport)
        logger.warning("Nokia live mode requested without credentials; using simulator mock.")
        return MockNokiaDeviceNetworkProvider(source_mode="nokia_simulator")
    source_mode = configured_source_mode(settings.nokia_network_api_enabled, mode)
    if mode == "disabled":
        return DisabledDeviceNetworkProvider()
    return MockNokiaDeviceNetworkProvider(source_mode=source_mode)
