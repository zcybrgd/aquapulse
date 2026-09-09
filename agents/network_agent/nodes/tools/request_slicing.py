import os
import requests
from typing import List, Dict, Any
from langchain_core.tools import tool
from dotenv import load_dotenv
from agents.network_agent.camara_api import camara_service

load_dotenv()

url = os.getenv("WEBHOOK_URL", "https://example.com")
notification_url = f"{url}/notifications"
print(f"Webhook URL: {url}")
print(f"Notification URL: {notification_url}")
notification_auth_token = os.getenv("NOTIFICATION_AUTH_TOKEN", "Bearer test-token")

@tool
def request_network_slice(
    devices: List[Dict[str, Any]], 
    slice_name: str,
    incident_context: List[Dict[str, Any]],
    mcc: str = "236",
    mnc: str = "30",
    service_type: int = 1,
    differentiator: str = "AUTO",  
    customer_name: str = "AquaPulse Customer",
    customer_description: str = "Dynamic Slicing Session"
) -> Dict[str, Any]:
    """
    Creates a 5G Network Slice asynchronously and registers device attachment 
    metadata with the background lifecycle server.
    Args:
     incident_context: One entry per device, each containing
          {"phone_number": str, "incident_id": str, "cluster_id": str,
                     "severity_tier": int}. Required so the lifecycle watcher can
            emit a per-incident NetworkGrant/NetworkDenied once the slice
            resolves. Copy these values verbatim from the input requests
    """
    try:
        formatted_devices = []
        for idx, dev in enumerate(devices):
            phone_number = dev.get("phone_number") or dev.get("device_id")
            raw_imsi = dev.get("imsi")
            imsi_val = int(raw_imsi) if raw_imsi is not None else (99999991000 + idx)
            formatted_devices.append({
                "phone_number": phone_number,
                "imsi": imsi_val,
                "status": "PENDING_ATTACHMENT"
            })

        my_slice, clean_name, diff_val = camara_service.create_slice(
            slice_name=slice_name,
            mcc=mcc,
            mnc=mnc,
            service_type=service_type,
            differentiator=differentiator,
            notification_url=notification_url,
            notification_auth_token=notification_auth_token
        )
        
        slice_id = getattr(my_slice, "name", clean_name)

        # Call the api watcher that continues activating the slice and attaching devices in the background
        registration_payload = {
            "slice_id": slice_id,
            "devices": formatted_devices,
            "customer_name": customer_name,
            "customer_description": customer_description,
            "notification_url": notification_url,
           "notification_auth_token": notification_auth_token,
            "incident_context": incident_context,
        }
        
        try:
            resp = requests.post(
                f"{url}/register-slice-watcher", 
                json=registration_payload, 
                timeout=3
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Server returned HTTP {resp.status_code}")
        except Exception as req_err:
            print(f"[ERROR] Watcher registration failed: {req_err}. Auto-reaping slice to prevent core queue wedge.")
            try:
                camara_service.delete_slice_direct(slice_id)
            except Exception:
                pass
            return {
                "status": "FAILED",
                "grant_type": "network_slicing",
                "slice_id": slice_id,
                "devices": formatted_devices,
                 "incident_context": incident_context,
                "error": f"FastAPI webhook server unreachable ({req_err}). Slice auto-reaped to protect tenant queue."
            }

        return {
            "status": "INITIATED",
            "grant_type": "network_slicing",
            "slice_id": slice_id,
            "differentiator": diff_val,
            "devices": formatted_devices,
            "message": f"Slice '{slice_id}' (SD: {diff_val}) initiated successfully. Lifecycle manager monitoring activation."
        }

    except Exception as e:
        return {
            "status": "FAILED",
            "grant_type": "network_slicing",
            "slice_id": None,
            "devices": devices,
             "incident_context": incident_context,
            "error": str(e)
        }


if __name__ == "__main__":
    test_devices = [{"phone_number": "+99999991000", "imsi": 99999991000}]
    result = request_network_slice.invoke({
        "devices": test_devices,
        "slice_name": "test-slice-01"
    })
    print(result)