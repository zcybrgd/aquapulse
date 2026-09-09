from __future__ import annotations
import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger("actuation_agent.tools.aquapulse")


class AquaPulsePlatformClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout_seconds: float = 5.0,
        use_real_ingest: bool = False,  
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.use_real_ingest = use_real_ingest
        self._session = requests.Session()

    def _endpoint(self) -> str:
        if self.use_real_ingest:
            return f"{self.base_url}/api/integrations/agents/response/v1/results"
        return f"{self.base_url}/api/integrations/agents/contracts/response/v1/validate-response"

    def send(self, payload: Dict[str, Any], incident_id: str) -> Optional[Dict[str, Any]]:
        url = self._endpoint()
        try:
            response = self._session.post(url, json=payload, timeout=self.timeout_seconds)
            if response.status_code == 404 and not self.use_real_ingest:
                logger.error(
                    "aquapulse_endpoint_not_implemented incident_id=%s url=%s",
                    incident_id, url,
                )
                return None
            response.raise_for_status()
            body = response.json()
            if self.use_real_ingest:
                logger.info("aquapulse_ingest_ok incident_id=%s run_id=%s", incident_id, body.get("run_id"))
            else:
                logger.info(
                    "aquapulse_validate_result incident_id=%s valid=%s errors=%s",
                    incident_id, body.get("valid"), body.get("errors"),
                )
            return body
        except requests.RequestException as exc:
            logger.error("aquapulse_send_FAILED incident_id=%s error=%s", incident_id, exc)
            return None