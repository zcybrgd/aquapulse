from __future__ import annotations
import logging
from typing import Callable, Optional
from ..state import ActuationState
logger = logging.getLogger("response_agent.nodes.human_override")
OverridePoller = Callable[[str], Optional[str]]


def make_human_override_node(poll_for_response: OverridePoller,window_seconds: float = 120.0,poll_interval_seconds: float = 2.0,):
    def human_override_node(state: ActuationState) -> ActuationState:
        if not state.get("human_override_requested"):
            return state
        incident_id = state["incident_id"]
        trace = list(state.get("reasoning_trace", []))
        logger.info("human_override_window_CHECK incident_id=%s window_seconds=%.0f",incident_id, window_seconds,)
        response = poll_for_response(incident_id)
        if response is None:
            final = "timed_out"
            trace.append(f"Human override window ({window_seconds:.0f}s) closed without a response; "
                "autonomous action stands and is logged for retroactive review.")
        elif response == "overridden":
            final = "overridden"
            trace.append("Operator OVERRODE the autonomous valve isolation within the window.")
        else:
            final = "confirmed"
            trace.append("Operator explicitly confirmed the autonomous action.")
        logger.info("human_override_window_CLOSED incident_id=%s outcome=%s", incident_id, final)
        return {**state, "human_override_response": final, "reasoning_trace": trace}
    return human_override_node
