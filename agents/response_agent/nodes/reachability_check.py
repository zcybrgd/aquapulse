import logging
from typing import Any, Callable, Dict, Optional
from agents.response_agent.tools.reachability_client import (
    DeviceReachabilityClient,
    check_cluster_reachability,
)

logger = logging.getLogger("actuation_agent.nodes.reachability_check")


def reachability_check_node(
    state: Dict[str, Any],
    reachability_client: Optional[DeviceReachabilityClient] = None,
) -> Dict[str, Any]:
    """LangGraph node to verify reachability for desert clusters."""
    cluster_id = state.get("cluster_id") or state.get("device_id")
    incident_id = state.get("incident_id", "unknown")

    if not cluster_id or not str(cluster_id).startswith("cluster-desert-"):
        logger.error("reachability_check_node rejected non-desert target ID: %s", cluster_id)
        return {
            "reachable": True,
            "reachability": None,
            "error": f"Invalid target identifier '{cluster_id}'. Expected a desert cluster ID.",
        }

    status = None
    if reachability_client:
        try:
            if hasattr(reachability_client, "check"):
                status = reachability_client.check(cluster_id)
            elif hasattr(reachability_client, "check_reachability"):
                status = reachability_client.check_reachability(cluster_id)
        except Exception as exc:
            logger.warning("reachability_client call failed (%s); falling back to default checker.", exc)

    if status is None:
        status = check_cluster_reachability(cluster_id)

    reachable = getattr(status, "reachable", True) if status else True
    signal_quality = (
        getattr(status, "raw_signal_quality", getattr(status, "signal_quality", None))
        if status
        else None
    )

    logger.info(
        "reachability_check_node incident_id=%s cluster_id=%s reachable=%s",
        incident_id,
        cluster_id,
        reachable,
    )
    return {
        "reachable": reachable,
        "reachability": status,
        "cluster_id": cluster_id,
        "device_id": cluster_id,
        "signal_quality": signal_quality,
    }


def make_reachability_check_node(
    reachability_client: Optional[DeviceReachabilityClient] = None,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        return reachability_check_node(state, reachability_client=reachability_client)

    return node