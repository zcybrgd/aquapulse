import os
import re
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from agents.network_agent.camara_api import camara_service

load_dotenv()

logger = logging.getLogger("NMA.Tools.CheckCongestion")

notification_url = os.getenv("CONGESTION_NOTIFICATION_URL", "https://example.com/notifications")
notification_auth_token = os.getenv("CONGESTION_NOTIFICATION_AUTH_TOKEN", "Bearer test-token")

# Map cluster IDs to CAMARA test MSISDN numbers
CLUSTER_MSISDN_MAP = {
    "cluster-desert-042": "+99999991000",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991000",
    "cluster-desert-045": "+99999990404",
    "cluster-desert-046": "+99999991000",
}

DEFAULT_MSISDN = os.getenv("DEFAULT_DEVICE_MSISDN", "+990100000000")


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
def check_congestion(
    representative_device_id: str,
    zone_id: str,
) -> Dict[str, Any]:
    """
    Queries current network congestion level for a specific geographic zone.
    Uses a representative device ID from the zone to query the regional congestion.

    Args:
        representative_device_id (str): The phone number or device ID located in the zone.
        zone_id (str): The geographic zone identifier.
    """
    # Guarantee device identifier is in valid MSISDN format expected by CAMARA API
    msisdn = normalize_to_msisdn(representative_device_id)

    try:
        res = camara_service.check_congestion(
            representative_device_id=msisdn,
            zone_id=zone_id,
            notification_url=notification_url,
            notification_auth_token=notification_auth_token
        )

        # Handle API status failures (400, 404, 500) gracefully for sandbox testing
        if isinstance(res, dict) and res.get("status") == "FAILED":
            error_str = str(res.get("error", ""))
            logger.warning(
                f"Congestion check returned FAILED for zone '{zone_id}' (device '{msisdn}'): {error_str}. "
                "Falling back to LOW congestion mock response."
            )
            return {
                "status": "SUCCESS",
                "zone_id": zone_id,
                "congestion_level": "LOW",
                "mocked": True,
                "info": f"Mocked low congestion due to API error: {error_str}"
            }

        return res

    except Exception as e:
        logger.error(
            f"Exception during check_congestion call for zone '{zone_id}': {e}. "
            "Defaulting to LOW congestion state."
        )
        return {
            "status": "SUCCESS",
            "zone_id": zone_id,
            "congestion_level": "LOW",
            "mocked": True,
            "info": f"Mocked low congestion due to exception: {e}"
        }