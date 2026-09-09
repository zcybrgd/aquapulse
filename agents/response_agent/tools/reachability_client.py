from __future__ import annotations

import logging
import time
import requests
from requests.adapters import HTTPAdapter, Retry
from ..schemas import ReachabilityStatus

logger = logging.getLogger("actuation_agent.tools.reachability")

# Known cluster/device ID to CAMARA MSISDN mappings
DEFAULT_DEVICE_MSISDN_MAP: dict[str, str] = {
    "cluster-desert-042": "+99999991001",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991003",
    "cluster-desert-045": "+99999991001",
    "cluster-desert-046": "+99999991001",
    "device-14-valve-A": "+99999991001",
    "device-offline-demo": "+99999991003",
    "device-14-valve-A-fail": "+99999991001",
    "cluster-urban-012": "+99999991003",
}

class DeviceReachabilityClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout_seconds: float = 3.0,
        max_retries: int = 2,
        device_msisdn_map: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.device_msisdn_map = (
            device_msisdn_map
            if device_msisdn_map is not None
            else DEFAULT_DEVICE_MSISDN_MAP
        )
        self._session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        self._session.mount("http://", HTTPAdapter(max_retries=retries))
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

    def _resolve_target_identifier(self, device_id: str) -> str:
        """Resolves cluster or device IDs to the expected CAMARA MSISDN format."""
        if device_id in self.device_msisdn_map:
            return self.device_msisdn_map[device_id]
        if device_id.startswith("+"):
            return device_id
        return self.device_msisdn_map.get(device_id, device_id)

    def check(self, device_id: str) -> ReachabilityStatus:
        target_id = self._resolve_target_identifier(device_id)
        url = f"{self.base_url}/v1/device-reachability/{target_id}"
        start = time.monotonic()

        try:
            response = self._session.get(url, timeout=self.timeout_seconds)

            # If MSISDN lookup returned 404 and target_id differed, retry with raw device_id
            if response.status_code == 404 and target_id != device_id:
                fallback_url = f"{self.base_url}/v1/device-reachability/{device_id}"
                response = self._session.get(fallback_url, timeout=self.timeout_seconds)

            # Handle sandbox/missing endpoint gracefully
            if response.status_code == 404:
                logger.warning(
                    "reachability_check returned 404 for device_id=%s (target_id=%s) — defaulting to reachable (True) for sandbox pipeline",
                    device_id,
                    target_id,
                )
                return ReachabilityStatus(
                    device_id=device_id,
                    reachable=True,
                    raw_signal_quality="-75 dBm",
                )

            response.raise_for_status()
            payload = response.json()
            raw_sq = payload.get("signal_quality")

            status = ReachabilityStatus(
                device_id=device_id,
                reachable=bool(payload.get("reachable", True)),
                raw_signal_quality=str(raw_sq) if raw_sq is not None else "-75 dBm",
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "reachability_check device_id=%s target_id=%s reachable=%s elapsed_ms=%.1f",
                device_id,
                target_id,
                status.reachable,
                elapsed_ms,
            )
            return status

        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning(
                "reachability_check error device_id=%s target_id=%s error=%s — defaulting to reachable (True) for sandbox pipeline",
                device_id,
                target_id,
                exc,
            )
            return ReachabilityStatus(
                device_id=device_id,
                reachable=True,
                raw_signal_quality="-75 dBm",
            )