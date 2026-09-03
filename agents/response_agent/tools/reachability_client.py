from __future__ import annotations
import logging
import time
import requests
from requests.adapters import HTTPAdapter, Retry
from ..schemas import ReachabilityStatus
logger = logging.getLogger("actuation_agent.tools.reachability")

class DeviceReachabilityClient:
    def __init__(self,base_url: str = "http://localhost:8001",timeout_seconds: float = 3.0,max_retries: int = 2,) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()
        retries = Retry(total=max_retries,backoff_factor=0.3,status_forcelist=(500, 502, 503, 504),allowed_methods=frozenset({"GET"}),)
        self._session.mount("http://", HTTPAdapter(max_retries=retries))
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

    def check(self, device_id: str) -> ReachabilityStatus:
        url = f"{self.base_url}/v1/device-reachability/{device_id}"
        start = time.monotonic()
        try:
            response = self._session.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            status = ReachabilityStatus(device_id=device_id,reachable=bool(payload.get("reachable", False)),raw_signal_quality=payload.get("signal_quality"),)
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info("reachability_check device_id=%s reachable=%s elapsed_ms=%.1f",device_id, status.reachable, elapsed_ms,)
            return status
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("reachability_check FAILED device_id=%s error=%s — failing closed (unreachable)",device_id, exc,)
            return ReachabilityStatus(device_id=device_id, reachable=False)
