"""
Nokia Network-as-Code (NaC) CAMARA API client wrappers (Section 5.B, Section 9 Phase 1).

Exposes two calls used by Stage 2 (Anomaly Investigation):
  - Device Reachability Status API
  - Congestion Insights API

Every call is wrapped so that a platform-side failure (auth failure, socket
error, timeout, non-2xx response) is surfaced as `api_unavailable=True`
rather than being misread as a legitimate UNREACHABLE/HIGH-congestion
reading (Section 5.B.3). The AIA must NEVER infer a classification from a
failed API call.

Two implementations are provided:
  - `MockCamaraClient`: deterministic, scenario-driven client used for
    local development, unit tests, and demos (no network access required).
  - `HttpCamaraClient`: thin `httpx`-based client for the live/sandbox
    Nokia NaC endpoints, following the "raw diagnostic requests first"
    guidance in Section 9 Phase 1. OAuth2 bearer token is injected via the
    `token_provider` callable so token refresh logic stays outside this class.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from aia.config import CONGESTION_HIGH, CONGESTION_LOW, CONGESTION_MEDIUM
from aia.models import CongestionLevel, ReachabilityStatus


class CamaraApiError(Exception):
    """Raised internally by client implementations; always caught at the call site."""


@dataclass
class ReachabilityResult:
    status: Optional[ReachabilityStatus]
    api_unavailable: bool
    error_detail: Optional[str] = None


@dataclass
class CongestionResult:
    level: Optional[CongestionLevel]
    api_unavailable: bool
    error_detail: Optional[str] = None


class CamaraClient(Protocol):
    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult: ...
    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult: ...


def safe_get_device_reachability_status(
    client: CamaraClient, sensor_cluster_id: str
) -> ReachabilityResult:
    """try/except wrapper (Section 5.B.3) around Device Reachability Status."""
    try:
        return client.get_device_reachability_status(sensor_cluster_id)
    except Exception as exc:  # noqa: BLE001 - platform failures must never propagate
        return ReachabilityResult(status=None, api_unavailable=True, error_detail=str(exc))


def safe_get_congestion_insights(
    client: CamaraClient, sensor_cluster_id: str
) -> CongestionResult:
    """try/except wrapper (Section 5.B.3) around Congestion Insights."""
    try:
        return client.get_congestion_insights(sensor_cluster_id)
    except Exception as exc:  # noqa: BLE001
        return CongestionResult(level=None, api_unavailable=True, error_detail=str(exc))


# ---------------------------------------------------------------------------
# Mock client -- deterministic scenario overrides + random fallback.
# Used for tests, demos, and Scenario A-E validation (Section 9 Phase 3).
# ---------------------------------------------------------------------------

@dataclass
class MockCamaraClient:
    """
    Deterministic mock CAMARA client.

    `overrides` lets tests pin exact responses per cluster id, e.g.:

        MockCamaraClient(overrides={
            "cluster-desert-042": {
                "reachability": ReachabilityStatus.REACHABLE,
                "congestion": CongestionLevel.LOW,
            }
        })

    Setting `"raise": True` for a cluster simulates an API outage
    (Scenario D), which the safe_* wrappers above convert to
    api_unavailable=True.
    """
    overrides: dict[str, dict] = field(default_factory=dict)
    seed: int = 7

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult:
        cfg = self.overrides.get(sensor_cluster_id, {})
        if cfg.get("raise"):
            raise CamaraApiError(f"Simulated Nokia NaC outage for {sensor_cluster_id}")
        status = cfg.get("reachability")
        if status is None:
            status = self._rng.choice([ReachabilityStatus.REACHABLE, ReachabilityStatus.UNREACHABLE])
        return ReachabilityResult(status=status, api_unavailable=False)

    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult:
        cfg = self.overrides.get(sensor_cluster_id, {})
        if cfg.get("raise"):
            raise CamaraApiError(f"Simulated Nokia NaC outage for {sensor_cluster_id}")
        level = cfg.get("congestion")
        if level is None:
            level = self._rng.choice([CongestionLevel.LOW, CongestionLevel.MEDIUM, CongestionLevel.HIGH])
        return CongestionResult(level=level, api_unavailable=False)


# ---------------------------------------------------------------------------
# HTTP client for the live Nokia NaC CAMARA sandbox / production endpoints.
# ---------------------------------------------------------------------------

class HttpCamaraClient:
    """
    Thin HTTP wrapper around the Nokia NaC CAMARA Device Reachability Status
    and Congestion Insights APIs. Endpoint paths follow the CAMARA API Hub
    naming convention; confirm exact paths/schemas against the live sandbox
    per Section 9 Phase 1 before relying on this in production, since path
    and payload details vary by NaC deployment/tenant.
    """

    def __init__(
        self,
        base_url: str,
        token_provider: Callable[[], str],
        timeout_seconds: float = 3.0,
    ):
        import httpx  # imported lazily so httpx is an optional dependency

        self._httpx = httpx
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._timeout = timeout_seconds

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token_provider()}"}

    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult:
        resp = self._httpx.post(
            f"{self._base_url}/device-reachability-status/v0/retrieve",
            json={"device": {"networkAccessIdentifier": sensor_cluster_id}},
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        raw_status = str(payload.get("reachabilityStatus", "")).upper()
        status = ReachabilityStatus.REACHABLE if raw_status == "REACHABLE" else ReachabilityStatus.UNREACHABLE
        return ReachabilityResult(status=status, api_unavailable=False)

    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult:
        resp = self._httpx.post(
            f"{self._base_url}/congestion-insights/v0/insights",
            json={"device": {"networkAccessIdentifier": sensor_cluster_id}},
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        raw_level = str(payload.get("congestionLevel", "")).upper()
        level_map = {
            CONGESTION_HIGH: CongestionLevel.HIGH,
            CONGESTION_MEDIUM: CongestionLevel.MEDIUM,
            CONGESTION_LOW: CongestionLevel.LOW,
        }
        level = level_map.get(raw_level, CongestionLevel.UNAVAILABLE)
        return CongestionResult(level=level, api_unavailable=False)
