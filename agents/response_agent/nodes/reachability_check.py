import logging
from typing import Dict, Any, Callable
from agents.response_agent.tools.reachability_client import check_cluster_reachability

logger = logging.getLogger("actuation_agent.nodes.reachability_check")


def reachability_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to verify reachability for desert clusters."""
    # Prioritize cluster_id over generic device_id
    cluster_id = state.get("cluster_id") or state.get("device_id")
    incident_id = state.get("incident_id", "unknown")

    if not cluster_id or not str(cluster_id).startswith("cluster-desert-"):
        logger.error("reachability_check_node rejected non-desert target ID: %s", cluster_id)
        return {
            "reachable": False,
            "error": f"Invalid target identifier '{cluster_id}'. Expected a desert cluster ID.",
        }

    status = check_cluster_reachability(cluster_id)
    
    logger.info(
        "reachability_check_node incident_id=%s cluster_id=%s reachable=%s",
        incident_id,
        cluster_id,
        status.reachable,
    )
    return {
        "reachable": status.reachable,
        "cluster_id": cluster_id,
        "device_id": cluster_id,
        "signal_quality": status.raw_signal_quality,
    }


def make_reachability_check_node() -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    return reachability_check_node