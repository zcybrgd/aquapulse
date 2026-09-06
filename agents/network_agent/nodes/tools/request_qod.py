import os
import time
from typing import Any, Dict
from dotenv import load_dotenv
from langchain_core.tools import tool
from network_as_code import NetworkAsCodeApi

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

@tool
def request_qod(
    device_id: str, 
    app_server_ipv4: str, 
    qos_profile: str, 
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
    try:
        response = nac_client.qod.create_session_v1(
            device={"phone_number": device_id},
            application_server={"ipv4Address": app_server_ipv4},
            qos_profile=qos_profile,
            duration=duration_seconds
        )

        session_id = getattr(response, "session_id", None)
        if not session_id:
            return {"status": "FAILED", "error": "No session_id returned from API gateway"}

        current_status = getattr(response, "qos_status", getattr(response, "status", "REQUESTED"))
        started_at = getattr(response, "started_at", None)
        expires_at = getattr(response, "expires_at", None)

        if wait_for_allocation and current_status == "REQUESTED":
            start_time = time.time()
            poll_interval = 2  # Check status every 2 seconds

            while (time.time() - start_time) < max_wait_seconds:
                time.sleep(poll_interval)
                try:
                    session_update = nac_client.qod.get_session_v1(session_id=session_id)
                    current_status = getattr(session_update, "qos_status", getattr(session_update, "status", current_status))
                    started_at = getattr(session_update, "started_at", None) or started_at
                    expires_at = getattr(session_update, "expires_at", None) or expires_at

                    # Break loop when terminal or active state is reached
                    if current_status in ["AVAILABLE", "UNAVAILABLE", "FAILED"]:
                        break
                except Exception:
                    # Ignore transient polling network errors and continue next loop
                    pass

        return {
            "session_id": session_id,
            "status": current_status,
            "qos_profile": getattr(response, "qos_profile", qos_profile),
            "started_at": str(started_at) if started_at is not None else ("Pending Activation" if current_status == "REQUESTED" else "N/A"),
            "expires_at": str(expires_at) if expires_at is not None else ("Pending Activation" if current_status == "REQUESTED" else "N/A")
        }

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

if __name__ == "__main__":
    test_payload = {
        "device_id": "+99999991000",
        "app_server_ipv4": "233.252.0.2",
        "qos_profile": "QOS_L",
        "duration_seconds": 3600,
        "wait_for_allocation": True,
        "max_wait_seconds": 10
    }
    result = request_qod.invoke(test_payload)
    print(result)