from __future__ import annotations
import logging
from typing import Literal, Optional
import requests

logger = logging.getLogger("actuation_agent.tools.network_release")


class NetworkReleaseClient:
    """Releases a previously-granted network guarantee (QoD session or slice)
    once an incident's actuation lifecycle has completed. Best-effort: a
    failure here must never re-open or reverse an already-closed incident."""

    def __init__(self, base_url: str = "http://localhost:8004", timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def release(
        self,
        guarantee_type: Literal["QoD", "slice"],
        session_id: str,
        incident_id: str,
    ) -> Optional[str]:
        """Returns a short status string, or None if the release could not be confirmed."""
        path = "/v1/qod/release" if guarantee_type == "QoD" else "/v1/slice/release"
        url = f"{self.base_url}{path}"
        body = {"session_id": session_id, "incident_id": incident_id}
        try:
            response = self._session.post(url, json=body, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status", "UNKNOWN")
            logger.info(
                "network_release_ok guarantee_type=%s session_id=%s incident_id=%s status=%s",
                guarantee_type, session_id, incident_id, status,
            )
            return status
        except requests.RequestException as exc:
            logger.error(
                "network_release_FAILED guarantee_type=%s session_id=%s incident_id=%s error=%s",
                guarantee_type, session_id, incident_id, exc,
            )
            return None