import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from agents.network_agent.camara_api import camara_service

load_dotenv()

notification_url = os.getenv("CONGESTION_NOTIFICATION_URL", "https://example.com/notifications")
notification_auth_token = os.getenv("CONGESTION_NOTIFICATION_AUTH_TOKEN", "Bearer test-token")

@tool
def check_congestion(
    representative_device_id: str,
    zone_id: str,
) -> Dict[str, Any]:
    """
    Queries current network congestion level for a specific geographic zone.
    Uses a representative device ID from the zone to query the regional congestion.
    
    Args:
        representative_device_id (str): The phone number of a device located in the zone.
        zone_id (str): The geographic zone identifier.
    """
    return camara_service.check_congestion(
        representative_device_id=representative_device_id,
        zone_id=zone_id,
        notification_url=notification_url,
        notification_auth_token=notification_auth_token
    )