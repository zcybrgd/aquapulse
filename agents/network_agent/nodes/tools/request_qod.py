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

# Explicit mapping of physical asset device IDs and cluster IDs to Nokia CAMARA test MSISDNs
DEVICE_MSISDN_MAP: dict[str, str] = {
    # Physical Device Assets
    "device-14-valve-A": "+99999991000",
    # Telemetry Clusters
    "cluster-desert-042": "+99999991000",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991000",
    "cluster-desert-045": "+99999990404",
    "cluster-desert-046": "+99999991000",
}

# Alias for backward compatibility
CLUSTER_MSISDN_MAP = DEVICE_MSISDN_MAP


def normalize_to_msisdn(device_or_cluster_id: str) -> str:
    """Translates cluster/device identifiers into standard E.164 MSISDN format (+1234567890).
    
    Raises:
        ValueError: If the identifier is unmapped and not a valid E.164 MSISDN.
    """
    if not device_or_cluster_id:
        raise ValueError("Device or cluster identifier cannot be empty.")

    # 1. Direct lookup in device/cluster map
    if device_or_cluster_id in DEVICE_MSISDN_MAP:
        return DEVICE_MSISDN_MAP[device_or_cluster_id]

    # 2. Check if already a valid E.164 phone number (+ followed by 10 to 15 digits)
    if re.match(r"^\+\d{10,15}$", device_or_cluster_id):
        return device_or_cluster_id

    # 3. Fail fast without silent fallback defaults
    raise ValueError(
        f"Identifier '{device_or_cluster_id}' is neither a recognized asset/cluster ID "
        f"nor a valid E.164 phone number. Please update DEVICE_MSISDN_MAP."
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
    Triggers CAMARA Quality on Demand (QoD) to prioritize connection between a device and an application server.
    Polls the network gateway until allocation transitions from 'REQUESTED' to 'AVAILABLE'.

    Args:
        device_id (string type): The physical asset ID (e.g., 'device-14-valve-A'), cluster ID (e.g., 'cluster-desert-046'), or E.164 MSISDN.
        qos_profile (string type): The CAMARA QoS profile label ('QOS_E', 'QOS_L', 'QOS_M', 'QOS_S').
        app_server_ipv4 (string type): The IPv4 address of the application server.
        duration_seconds (integer type): Session length in seconds (up to 86400).
        wait_for_allocation (boolean type): Whether to poll until status is AVAILABLE or max_wait_seconds expires.
        max_wait_seconds (integer type): Max duration in seconds to wait for allocation confirmation.
    """
    # Guarantee app_server_ipv4 is never None or empty
    if not app_server_ipv4:
        app_server_ipv4 = DEFAULT_APP_SERVER_IPV4

    # Resolve device identifier to E.164 MSISDN strictly
    msisdn = normalize_to_msisdn(device_id)

    return camara_service.request_qod(
        device_id=msisdn,
        app_server_ipv4=app_server_ipv4,
        qos_profile=qos_profile,
        duration_seconds=duration_seconds,
        wait_for_allocation=wait_for_allocation,
        max_wait_seconds=max_wait_seconds
    )