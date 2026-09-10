import os
import json
import time
import logging
import threading
import uuid
import redis
from typing import Optional
from urllib.parse import urlparse
from pydantic import ValidationError
from agents.network_agent.graph import graph
from agents.network_agent.schemas import BatchInput, InvestigatedThreat
from agents.network_agent.camara_api import camara_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("NMA.Runner")

_redis_url = os.getenv("REDIS_URL")
if _redis_url:
    _parsed = urlparse(_redis_url)
    REDIS_HOST = _parsed.hostname or "127.0.0.1"
    REDIS_PORT = int(_parsed.port or 6379)
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CHANNEL = "aia:results"

url = os.getenv("WEBHOOK_URL", "https://example.com")
notification_url = f"{url}/notifications"
notification_auth_token = os.getenv("NOTIFICATION_AUTH_TOKEN", "Bearer test-token")


def create_preprovisioned_slice(
    slice_base_name: str = "slice-z47-1788620730",
    mcc: str = "236",
    mnc: str = "30",
    max_wait_seconds: int = 500
) -> Optional[str]:
    """
    Ensures a mission-critical 5G slice is active in OPERATING state at startup.
    Recreates the slice if absent or in a terminal state (DELETED/FAILED/REJECTED).
    """
    logger.info(f"[Startup] Checking pre-provisioned Mission-Critical Slice '{slice_base_name}'...")
    slice_id = slice_base_name

    try:
        current_state = camara_service.get_slice_state(slice_id)
        logger.info(f"Existing slice '{slice_id}' found in state: '{current_state}'.")
    except Exception:
        current_state = "NOT_FOUND"

    # Trigger creation if not found OR if existing slice is in an inactive/terminal state
    if current_state in ["NOT_FOUND", "DELETED", "FAILED", "REJECTED"]:
        # Append unique suffix if replacing a deleted/failed slice to prevent name collision in NaC
        if current_state != "NOT_FOUND":
            slice_id = f"{slice_base_name}-{uuid.uuid4().hex[:6]}"
            logger.info(f"Previous slice was '{current_state}'. Using new unique ID: '{slice_id}'")

        try:
            logger.info(f"Requesting creation of slice '{slice_id}'...")
            my_slice, clean_name, _ = camara_service.create_slice(
                slice_name=slice_id,
                mcc=mcc,
                mnc=mnc,
                service_type=2,  # URLLC
                differentiator="AUTO",
                notification_url=notification_url,
                notification_auth_token=notification_auth_token
            )
            slice_id = getattr(my_slice, "name", getattr(my_slice, "id", clean_name))
        except Exception as create_err:
            logger.error(f"[ERROR] Failed to initiate slice creation: {create_err}")
            os.environ["PREPROVISIONED_SLICE_ID"] = ""
            return None

    # Poll state until OPERATING
    start_time = time.time()
    activation_requested = False

    while (time.time() - start_time) < max_wait_seconds:
        try:
            current_state = camara_service.get_slice_state(slice_id)
            logger.info(f"Slice '{slice_id}' current state: '{current_state}'.")
        except Exception as state_err:
            logger.warning(f"Could not retrieve state for slice '{slice_id}': {state_err}")
            current_state = "UNKNOWN"

        if current_state == "OPERATING":
            logger.info(f"Mission-Critical Slice '{slice_id}' is ACTIVE & OPERATING!")
            os.environ["PREPROVISIONED_SLICE_ID"] = slice_id
            return slice_id

        elif current_state == "AVAILABLE":
            if not activation_requested:
                logger.info(f"Slice '{slice_id}' is AVAILABLE. Sending activation request...")
                try:
                    camara_service.activate_slice(slice_id)
                    activation_requested = True
                except Exception as act_err:
                    logger.warning(f"Activation call notice: {act_err}")

        # Break loop immediately if the slice enters any unrecoverable state
        elif current_state in ["FAILED", "REJECTED", "DELETED"]:
            logger.error(f"Slice '{slice_id}' entered terminal state: '{current_state}'. Stopping poll.")
            break

        time.sleep(3)

    logger.error(
        f"[ERROR] Slice '{slice_id}' failed to reach OPERATING state within {max_wait_seconds}s. "
        f"Cleaning up..."
    )
    
    try:
        camara_service.delete_slice_direct(slice_id)
        logger.info(f"Successfully cleaned up stalled slice '{slice_id}'.")
    except Exception as del_err:
        logger.warning(f"Could not delete stalled slice '{slice_id}': {del_err}")

    os.environ["PREPROVISIONED_SLICE_ID"] = ""
    logger.error("[CRITICAL] Pre-provisioning failed. No active 5G slice is available for this run.")
    return None


def process_threats(threats: list[dict]):
    actionable_requests = [
        t for t in threats 
        if t.get("severity_tier", 1) >= 2 or t.get("network_status", {}).get("network_degradation_detected", False)
    ]

    if not actionable_requests:
        logger.info("No actionable threats requiring network QoS/Slicing in this payload.")
        return

    logger.info("Triggering NMA LangGraph for %d threat(s)...", len(actionable_requests))

    initial_input = {
        "raw_requests": actionable_requests,
        "messages": []
    }

    try:
        final_state = graph.invoke(initial_input)
        output_payload = {}
        for key, value in final_state.items():
            if key == "messages":
                output_payload["messages"] = [
                    {
                        "role": getattr(msg, "type", type(msg).__name__),
                        "content": getattr(msg, "content", str(msg)),
                        "tool_calls": getattr(msg, "tool_calls", [])
                    }
                    for msg in value
                ]
            else:
                output_payload[key] = value

        json_output = json.dumps(output_payload, indent=2, default=str)
        logger.info(f"NMA Workflow Completed:\n{json_output}")

    except Exception as e:
        logger.error(f"Error during NMA execution: {e}", exc_info=True)


def start_readiness_server(port: int | None = None) -> None:
    """Serve GET /health for AquaPulse readiness probes. No /v1/contract."""
    from fastapi import FastAPI
    import uvicorn

    listen_port = int(port or os.getenv("NETWORK_AGENT_PORT", "9001"))
    health_app = FastAPI(title="AquaPulse Network Agent Readiness")

    @health_app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "network_management_agent"}

    config = uvicorn.Config(health_app, host="0.0.0.0", port=listen_port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, name="nma-health", daemon=True).start()
    logger.info("NMA readiness server listening on http://127.0.0.1:%s/health", listen_port)


def start_listener():
    logger.info("Connecting to Redis at %s:%d...", REDIS_HOST, REDIS_PORT)
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)

    logger.info(f"NMA Agent listening on Redis channel '{REDIS_CHANNEL}'...")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            raw_data = message["data"].decode("utf-8")
            payload = json.loads(raw_data)
            threats = []

            if "investigated_threats" in payload:
                batch = BatchInput.model_validate(payload)
                threats = [t.model_dump() for t in batch.investigated_threats]
            elif "anomaly_id" in payload:
                threat = InvestigatedThreat.model_validate(payload)
                threats = [threat.model_dump()]

            if threats:
                process_threats(threats)

        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning("Ignored non-matching payload on '%s': %s", REDIS_CHANNEL, err)
        except Exception as e:
            logger.error("Unexpected error processing Redis message: %s", e, exc_info=True)



if __name__ == "__main__":
    start_readiness_server()
    # Create the pre-provisioned slice on startup
    create_preprovisioned_slice()
    start_listener()