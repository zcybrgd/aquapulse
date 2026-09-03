from __future__ import annotations
import logging
from ..state import ActuationState
from ..tools.reachability_client import DeviceReachabilityClient
logger = logging.getLogger("actuation_agent.nodes.reachability_check")

def make_reachability_check_node(client: DeviceReachabilityClient):
    def reachability_check_node(state: ActuationState) -> ActuationState:
        device_id = state["device_id"]
        incident_id = state["incident_id"]
        status = client.check(device_id)
        trace = list(state.get("reasoning_trace", []))
        if status.reachable:
            trace.append(f"Device {device_id} confirmed reachable "
                f"(signal_quality={status.raw_signal_quality}) : proceeding to actuation.")
        else:
            trace.append(f"Device {device_id} is UNREACHABLE. Cannot safely send a command ; "
                "escalating to human operator instead of firing blind.")
        logger.info("reachability_check_node incident_id=%s device_id=%s reachable=%s",
            incident_id, device_id, status.reachable,)
        return {**state, "reachability": status, "reasoning_trace": trace}
    return reachability_check_node
reachability_check_node = make_reachability_check_node(DeviceReachabilityClient())
