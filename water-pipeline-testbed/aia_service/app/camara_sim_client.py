"""
Implements the AIA's `CamaraClient` protocol by querying the simulator's
`/network_status/{cluster_id}` endpoint, so the already-built Anomaly
Investigation Agent runs completely unmodified against simulated network
conditions instead of a mock or the real Nokia NaC platform.

Network/HTTP failures are surfaced by *raising*, exactly like the
`MockCamaraClient`'s `raise` override in the AIA's own test suite -- the
AIA's `safe_get_*` wrappers (in `aia/camara_client.py`) catch these and turn
them into `api_unavailable=True`, so a simulator outage or timeout correctly
exercises the AIA's `insufficient_data` path.
"""
from __future__ import annotations

import httpx

from aia.camara_client import CamaraApiError, CongestionResult, ReachabilityResult
from aia.models import CongestionLevel, ReachabilityStatus

_CONGESTION_MAP = {
    "LOW": CongestionLevel.LOW,
    "MEDIUM": CongestionLevel.MEDIUM,
    "HIGH": CongestionLevel.HIGH,
}


class SimulatedCamaraClient:
    def __init__(self, simulator_url: str, timeout_seconds: float = 3.0):
        self._base_url = simulator_url.rstrip("/")
        self._timeout = timeout_seconds

    def _fetch(self, sensor_cluster_id: str) -> dict:
        try:
            resp = httpx.get(
                f"{self._base_url}/network_status/{sensor_cluster_id}",
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise CamaraApiError(f"Simulator network_status call failed: {exc}") from exc

    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult:
        data = self._fetch(sensor_cluster_id)
        status = ReachabilityStatus.REACHABLE if data.get("reachable") else ReachabilityStatus.UNREACHABLE
        return ReachabilityResult(status=status, api_unavailable=False)

    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult:
        data = self._fetch(sensor_cluster_id)
        level = _CONGESTION_MAP.get(str(data.get("congestion", "")).upper(), CongestionLevel.UNAVAILABLE)
        return CongestionResult(level=level, api_unavailable=False)
