# agents/network_agent/nodes/tools/request_qod.py

import os
import re
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv
from agents.network_agent.camara_api import camara_service

load_dotenv()

logger = logging.getLogger("NMA.Tools.RequestQoD")

DEFAULT_APP_SERVER_IPV4 = os.getenv("APP_SERVER_IPV4", "233.252.0.2")

# STRICT MAP: Desert clusters only
CLUSTER_MSISDN_MAP: dict[str, str] = {
    "cluster-desert-042": "+99999991000",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991000",
    "cluster-desert-045": "+99999990404",
    "cluster-desert-046": "+99999991000",
}


def normalize_to_msisdn(cluster_id: str) -> str:
    """Translates desert cluster IDs into standard Nokia CAMARA test MSISDN format."""
    if not cluster_id:
        raise ValueError("Cluster ID cannot be empty.")

    if cluster_id in CLUSTER_MSISDN_MAP:
        return CLUSTER_MSISDN_MAP[cluster_id]

    if re.match(r"^\+\d{10,15}$", cluster_id):
        return cluster_id

    raise ValueError(
        f"Identifier '{cluster_id}' is not a recognized desert cluster or valid E.164 MSISDN. "
        f"Allowed clusters: {list(CLUSTER_MSISDN_MAP.keys())}"
    )


@tool
def request_qod(
    device_id: str, 
    qos_profile: str, 
    app_server_ipv4: Optional[str] = None,
    duration_seconds: int = 3600,
    wait_for_allocation: bool = True,
    max_wait_seconds: int = 20
) -> Dict[str, Any]:
    """
    Triggers CAMARA Quality on Demand (QoD) for a desert cluster.

    Args:
        device_id (string type): Target cluster ID (e.g. 'cluster-desert-046') or E.164 MSISDN.
        qos_profile (string type): The CAMARA QoS profile label ('QOS_E', 'QOS_L', 'QOS_M', 'QOS_S').
        app_server_ipv4 (string type): The IPv4 address of the application server.
        duration_seconds (integer type): Session length in seconds.
        wait_for_allocation (boolean type): Whether to poll until status is AVAILABLE.
        max_wait_seconds (integer type): Max duration in seconds to wait for allocation confirmation.
    """
    if not app_server_ipv4:
        app_server_ipv4 = DEFAULT_APP_SERVER_IPV4

    msisdn = normalize_to_msisdn(device_id)

    return camara_service.request_qod(
        device_id=msisdn,
        app_server_ipv4=app_server_ipv4,
        qos_profile=qos_profile,
        duration_seconds=duration_seconds,
        wait_for_allocation=wait_for_allocation,
        max_wait_seconds=max_wait_seconds
    )