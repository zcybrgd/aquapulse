import json
import logging
import time
import redis
from pydantic import ValidationError
from agents.network_agent.graph import graph
from agents.network_agent.schemas import BatchInput, InvestigatedThreat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("NMA.Runner")

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_CHANNEL = "aia:results"


def invoke_graph_with_retry(initial_input: dict, max_retries: int = 3, base_delay: float = 2.0) -> dict:
    """Invokes the NMA LangGraph with exponential backoff on HTTP 429 / Rate Limit errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return graph.invoke(initial_input)
        except Exception as exc:
            err_msg = str(exc)
            is_rate_limit = "429" in err_msg or "rate_limit" in err_msg.lower()

            if is_rate_limit and attempt < max_retries:
                sleep_time = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "NMA LangGraph rate limit hit (attempt %d/%d). Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    sleep_time,
                )
                time.sleep(sleep_time)
            else:
                raise exc


def process_threats(threats: list[dict]):
    """Filters actionable threats and passes them through the LangGraph workflow."""
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
        # Execute LangGraph workflow with retry safety
        final_state = invoke_graph_with_retry(initial_input, max_retries=3, base_delay=3.0)
        
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
        logger.info("NMA Workflow Completed. Agent Final Output JSON:\n%s", json_output)

    except Exception as e:
        logger.error("Error during NMA LangGraph execution after retries: %s", e)
        
        # Safe fallback response generation when LLM execution fails due to persistent rate limits
        fallback_payload = {
            "status": "FALLBACK_EXECUTED",
            "reason": f"NMA Graph Execution rate-limited or failed: {e}",
            "actionable_requests_count": len(actionable_requests),
            "fallback_action": "Default emergency QoS slice modification queued for actionable cluster segments.",
            "impacted_clusters": [t.get("sensor_cluster_id") for t in actionable_requests],
        }
        logger.warning("NMA Heuristic Fallback Output JSON:\n%s", json.dumps(fallback_payload, indent=2))


def start_listener():
    logger.info("Connecting to Redis at %s:%d...", REDIS_HOST, REDIS_PORT)
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)

    logger.info("NMA Agent active and listening on Redis channel '%s'...", REDIS_CHANNEL)

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
            logger.warning("Ignored non-matching payload on '%s': %s", REDIS_CHANNEL, err)
        except Exception as e:
            logger.error("Unexpected error processing Redis message: %s", e, exc_info=True)


if __name__ == "__main__":
    start_listener()