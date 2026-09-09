from __future__ import annotations
import logging
from ..state import ActuationState
from ..tools.network_release_agent import NetworkReleaseClient

logger = logging.getLogger("actuation_agent.nodes.release_network")


def make_release_network_node(client: NetworkReleaseClient):
    def release_network_node(state: ActuationState) -> ActuationState:
        grant = state.get("network_grant")
        incident_id = state["incident_id"]
        trace = list(state.get("reasoning_trace", []))

        if grant is None:
            return {**state, "network_released": False, "network_release_status": None}

        status = client.release(
            guarantee_type=grant.guarantee_type,
            session_id=grant.session_id,
            incident_id=incident_id,)
        released = status is not None
        logger.warning("ATTEMPTING_RELEASE session_id=%s guarantee_type=%s incident_id=%s", grant.session_id, grant.guarantee_type, incident_id)
        if released:
            trace.append(
                f"Network guarantee released (guarantee_type={grant.guarantee_type}, "
                f"session_id={grant.session_id}, status={status})."
            )
        else:
            trace.append(
                f"Network guarantee release FAILED for session_id={grant.session_id}; "
                "resource may remain reserved — flagged for manual cleanup, not retried automatically."
            )
        logger.info(
            "release_network_node incident_id=%s released=%s status=%s",
            incident_id, released, status,
        )
        return {**state, "network_released": released, "network_release_status": status, "reasoning_trace": trace}

    return release_network_node