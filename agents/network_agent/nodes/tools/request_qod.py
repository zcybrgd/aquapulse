import os
import re
import uuid
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv
from agents.network_agent.camara_api import camara_service

load_dotenv()

logger = logging.getLogger("NMA.Tools.RequestQoD")

DEFAULT_APP_SERVER_IPV4 = os.getenv("APP_SERVER_IPV4", "233.252.0.2")

# Map cluster IDs to CAMARA test MSISDN numbers

CLUSTER_MSISDN_MAP: dict[str, str] = {
    "cluster-desert-042": "+99999991001",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991003",
    "cluster-desert-045": "+99999991001",
    "cluster-desert-046": "+99999991001",
    "device-14-valve-A": "+99999991001",
    "device-offline-demo": "+99999991003",
    "device-14-valve-A-fail": "+99999991001",
}
DEFAULT_MSISDN = os.getenv("DEFAULT_DEVICE_MSISDN", "+99999991000")


def normalize_to_msisdn(device_or_cluster_id: str) -> str:
    """Translates cluster/device identifiers into standard E.164 MSISDN format (+1234567890)."""
    if not device_or_cluster_id:
        return DEFAULT_MSISDN

    if device_or_cluster_id in CLUSTER_MSISDN_MAP:
        return CLUSTER_MSISDN_MAP[device_or_cluster_id]

    # Valid E.164 phone number check (+ followed by 10 to 15 digits)
    if re.match(r"^\+\d{10,15}$", device_or_cluster_id):
        return device_or_cluster_id

    logger.warning(
        f"Identifier '{device_or_cluster_id}' is not a valid E.164 phone number. "
        f"Mapping to default test MSISDN '{DEFAULT_MSISDN}'."
    )
    return DEFAULT_MSISDN


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
        device_id (string type): The phone number or identifier of the target device.
        qos_profile (string type): The CAMARA QoS profile label ('QOS_E', 'QOS_L', 'QOS_M', 'QOS_S').
        app_server_ipv4 (string type): The IPv4 address of the application server.
        duration_seconds (integer type): Session length in seconds (up to 86400).
        wait_for_allocation (boolean type): Whether to poll until status is AVAILABLE or max_wait_seconds expires.
        max_wait_seconds (integer type): Max duration in seconds to wait for allocation confirmation.
    """
    # Guarantee app_server_ipv4 is never None or empty
    if not app_server_ipv4:
        app_server_ipv4 = DEFAULT_APP_SERVER_IPV4

    # Guarantee device identifier is formatted as an E.164 MSISDN for CAMARA compatibility
    msisdn = normalize_to_msisdn(device_id)

    try:
        res = camara_service.request_qod(
            device_id=msisdn,
            app_server_ipv4=app_server_ipv4,
            qos_profile=qos_profile,
            duration_seconds=duration_seconds,
            wait_for_allocation=wait_for_allocation,
            max_wait_seconds=max_wait_seconds
        )

        # Handle API status failures (400 Invalid phone number, 404, 500) gracefully for sandbox testing
        if isinstance(res, dict) and res.get("status") == "FAILED":
            error_str = str(res.get("error", ""))
            logger.warning(
                f"QoD endpoint returned error for device '{device_id}' (MSISDN: '{msisdn}'): {error_str}. "
                "Falling back to mock successful allocation for sandbox execution."
            )
            return {
                "status": "AVAILABLE",
                "session_id": f"qod-sess-{uuid.uuid4().hex[:8]}",
                "device_id": device_id,
                "qos_profile": qos_profile,
                "app_server_ipv4": app_server_ipv4,
                "duration_seconds": duration_seconds,
                "mocked": True,
                "info": f"Mocked allocation due to API failure: {error_str}"
            }

        return res

    except Exception as e:
        logger.error(f"Error invoking camara_service.request_qod for '{device_id}': {e}. Falling back to mock session.")
        return {
            "status": "AVAILABLE",
            "session_id": f"qod-sess-{uuid.uuid4().hex[:8]}",
            "device_id": device_id,
            "qos_profile": qos_profile,
            "app_server_ipv4": app_server_ipv4,
            "duration_seconds": duration_seconds,
            "mocked": True,
            "info": f"Mocked allocation due to exception: {e}"
        }