import os
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv
from agents.network_agent.camara_api import camara_service

load_dotenv()

DEFAULT_APP_SERVER_IPV4 = os.getenv("APP_SERVER_IPV4", "233.252.0.2")

@tool
def request_qod(
    device_id: str, 
    qos_profile: str, 
    app_server_ipv4: Optional[str]= None,
    duration_seconds: int = 3600,
    wait_for_allocation: bool = True,
    max_wait_seconds: int = 20
) -> Dict[str, Any]:
    """
    Triggers CAMARA Quality on Demand (QoD) to prioritize connection between a device and an application server.
    Polls the network gateway until allocation transitions from 'REQUESTED' to 'AVAILABLE'.

    Args:
        device_id (string type): The phone number of the target device.
        app_server_ipv4 (string type): The IPv4 address of the application server.
        qos_profile (string type): The CAMARA QoS profile label ('QOS_E', 'QOS_L', 'QOS_M', 'QOS_S').
        duration_seconds (integer type): Session length in seconds (up to 86400).
        wait_for_allocation (boolean type): Whether to poll until status is AVAILABLE or max_wait_seconds expires.
        max_wait_seconds (integer type): Max duration in seconds to wait for allocation confirmation.
    """
    if not app_server_ipv4:
        app_server_ipv4 = DEFAULT_APP_SERVER_IPV4
    return camara_service.request_qod(
        device_id=device_id,
        app_server_ipv4=app_server_ipv4,
        qos_profile=qos_profile,
        duration_seconds=duration_seconds,
        wait_for_allocation=wait_for_allocation,
        max_wait_seconds=max_wait_seconds
    )

if __name__ == "__main__":
    test_payload = {
        "device_id": "+99999991000",
        "qos_profile": "QOS_L",
        "duration_seconds": 3600,
        "wait_for_allocation": True,
        "max_wait_seconds": 10
    }
    result = request_qod.invoke(test_payload)
    print(result)