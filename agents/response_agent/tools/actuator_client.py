from __future__ import annotations
import logging
import requests
logger = logging.getLogger("actuation_agent.tools.actuator")

class ValveCommandError(Exception):
    """Raised when a valve command could not be confirmed. Callers must
    treat this as an operational emergency"""
class ValveActuatorClient:
    def __init__(self, base_url: str = "http://localhost:8003", timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def isolate(self, device_id: str, incident_id: str) -> bool:
        url = f"{self.base_url}/v1/valve/isolate"
        body = {"device_id": device_id, "incident_id": incident_id, "action": "close"}
        try:
            response = self._session.post(url, json=body, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise ValveCommandError(f"Valve isolation command failed to reach device={device_id}: {exc}") from exc
        confirmed = bool(payload.get("confirmed", False))
        if not confirmed:
            raise ValveCommandError(f"Valve isolation command sent to device={device_id} but "
                f"actuator did not confirm closure. Raw response: {payload}")
        logger.critical("VALVE_ISOLATED device_id=%s incident_id=%s — confirmed by actuator",device_id, incident_id,)
        return True