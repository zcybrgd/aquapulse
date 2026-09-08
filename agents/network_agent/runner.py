import json
import logging
import redis
from pydantic import ValidationError
from agents.network_agent.graph import graph
from agents.network_agent.schemas import BatchInput, InvestigatedThreat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("NMA.Runner")

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_CHANNEL = "aia:results"

def process_threats(threats: list[dict]):
    """Filters actionable threats and passes them through the LangGraph workflow."""
    actionable_requests = [
        t for t in threats 
        if t.get("severity_tier", 1) >= 2 or t.get("network_status", {}).get("network_degradation_detected", False)
    ]

    if not actionable_requests:
        logger.info("No actionable threats requiring network QoS/Slicing in this payload.")
        return

    logger.info(f"Triggering NMA LangGraph for {len(actionable_requests)} threat(s)...")

    initial_input = {
        "raw_requests": actionable_requests,
        "messages": []
    }

    try:
        # Execute the LangGraph workflow: collect -> rank -> group -> network_agent
        final_state = graph.invoke(initial_input)
        
        # Format the state dictionary for clear JSON output
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
        
        # Log via logger.info so it flushes immediately to stdout
        logger.info(f"NMA Workflow Completed. Agent Final Output JSON:\n{json_output}")

    except Exception as e:
        logger.error(f"Error during NMA LangGraph execution: {e}", exc_info=True)


def start_listener():
    logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)

    logger.info(f"NMA Agent active and listening on Redis channel '{REDIS_CHANNEL}'...")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            raw_data = message["data"].decode("utf-8")
            payload = json.loads(raw_data)
            threats = []

            # Case A: BatchInput structure
            if "investigated_threats" in payload:
                batch = BatchInput.model_validate(payload)
                threats = [t.model_dump() for t in batch.investigated_threats]
            # Case B: Single InvestigatedThreat structure
            elif "anomaly_id" in payload:
                threat = InvestigatedThreat.model_validate(payload)
                threats = [threat.model_dump()]

            if threats:
                process_threats(threats)

        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(f"Ignored non-matching payload on '{REDIS_CHANNEL}': {err}")
        except Exception as e:
            logger.error(f"Unexpected error processing Redis message: {e}", exc_info=True)

if __name__ == "__main__":
    start_listener()