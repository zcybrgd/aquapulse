from __future__ import annotations
import logging
from ..state import ActuationState
from ..tools.aquapulse_adapter import to_response_result_v1
from ..tools.aquapulse_client import AquaPulsePlatformClient

logger = logging.getLogger("actuation_agent.nodes.publish_to_platform")


def make_publish_to_platform_node(client: AquaPulsePlatformClient):
    def publish_to_platform_node(state: ActuationState) -> ActuationState:
        entry = state.get("audit_entry")
        if entry is None:
            return state

        payload = to_response_result_v1(entry)
        result = client.send(payload, incident_id=state["incident_id"])

        trace = list(state.get("reasoning_trace", []))
        if result is not None and result.get("valid"):
            trace.append("Published to AquaPulse platform: payload validated successfully.")
        elif result is not None:
            trace.append(f"AquaPulse platform validation returned errors: {result.get('errors')}.")
        else:
            trace.append("AquaPulse platform publish failed (network/endpoint error); not retried automatically.")

        return {**state, "reasoning_trace": trace}

    return publish_to_platform_node