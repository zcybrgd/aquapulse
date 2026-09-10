import os
import json
import time
import logging
import threading
import uuid
import redis
from typing import Optional
from agents.network_agent.graph import graph
from agents.network_agent.camara_api import camara_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("NMA.Runner")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
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
    """Ensures a mission-critical 5G slice is active in OPERATING state at startup."""
    logger.info(f"[Startup] Checking pre-provisioned Mission-Critical Slice '{slice_base_name}'...")
    slice_id = slice_base_name

    try:
        current_state = camara_service.get_slice_state(slice_id)
        logger.info(f"Existing slice '{slice_id}' found in state: '{current_state}'.")
    except Exception:
        current_state = "NOT_FOUND"

    if current_state in ["NOT_FOUND", "DELETED", "FAILED", "REJECTED"]:
        if current_state != "NOT_FOUND":
            slice_id = f"{slice_base_name}-{uuid.uuid4().hex[:6]}"
            logger.info(f"Previous slice was '{current_state}'. Using new unique ID: '{slice_id}'")

        try:
            logger.info(f"Requesting creation of slice '{slice_id}'...")
            my_slice, clean_name, _ = camara_service.create_slice(
                slice_name=slice_id,
                mcc=mcc,
                mnc=mnc,
                service_type=2,
                differentiator="AUTO",
                notification_url=notification_url,
                notification_auth_token=notification_auth_token
            )
            slice_id = getattr(my_slice, "name", getattr(my_slice, "id", clean_name))
        except Exception as create_err:
            logger.error(f"[ERROR] Failed to initiate slice creation: {create_err}")
            os.environ["PREPROVISIONED_SLICE_ID"] = ""
            return None

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

        elif current_state in ["FAILED", "REJECTED", "DELETED"]:
            logger.error(f"Slice '{slice_id}' entered terminal state: '{current_state}'. Stopping poll.")
            break

        time.sleep(3)

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
        logger.info("NMA Workflow Completed successfully for %d request(s).", len(actionable_requests))
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

            raw_threats = payload.get("investigated_threats") or payload.get("threats") or []
            if not raw_threats and "anomaly_id" in payload:
                raw_threats = [payload]

            threats = []
            for t in raw_threats:
                if isinstance(t, dict):
                    if not t.get("device_id"):
                        t["device_id"] = t.get("sensor_cluster_id") or "cluster-desert-046"
                    threats.append(t)

            if threats:
                process_threats(threats)

        except Exception as e:
            logger.error("Unexpected error processing Redis message: %s", e, exc_info=True)


if __name__ == "__main__":
    create_preprovisioned_slice()
    start_listener()