from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from langchain_core.tools import tool
import os
from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

@tool
def check_congestion(
    representative_device_id: str,
    zone_id: str,
    notification_url: str,
    notification_auth_token: str
) -> Dict[str, Any]:
    """
    Queries current network congestion level for a specific geographic zone.
    Uses a representative device ID from the zone to query the regional congestion.
    
    Args:
        representative_device_id (str): The phone number of a device located in the zone.
        zone_id (str): The geographic zone identifier.
        notification_url (str): Webhook URL to receive ongoing congestion updates.
        notification_auth_token (str): Authentication token for the webhook.
    """
    try:
        nac_client.congestion_insights.create_subscription(
            device={"phone_number": representative_device_id},
            webhook={
                "notification_url": "https://application-server.com",
                "notification_auth_token": "c8974e592c2fa383d4a3960714",
            },
            subscription_expire_time=datetime.now(timezone.utc) + timedelta(days=1)
        )

        congestion_data = nac_client.congestion_insights.query(
            device={"phone_number": representative_device_id}
        )

        congestion_level = "None"
        if congestion_data and len(congestion_data) > 0:
            first_event = congestion_data[0]
            congestion_level = getattr(
                first_event, 
                "level", 
                getattr(first_event, "congestion_level", "Unknown")
            )
            
        return {
            "zone_id": zone_id,
            "representative_device_id": representative_device_id,
            "congestion_level": congestion_level
        }
        
    except Exception as e:
        return {
            "zone_id": zone_id,
            "representative_device_id": representative_device_id,
            "status": "FAILED", 
            "error": str(e)
        }

