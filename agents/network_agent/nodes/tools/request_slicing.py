import os
import re
import time
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_core.tools import tool
from network_as_code import NetworkAsCodeApi

load_dotenv()

nac_client = NetworkAsCodeApi(
    rapidapi_host=os.getenv("RAPIDAPI_HOST"),
    api_key=os.getenv("NOKIA_API_KEY")
)

def _get_slice_state(slice_obj: Any) -> str:
    """Helper to extract slice state from either SDK object or dictionary."""
    if isinstance(slice_obj, dict):
        return slice_obj.get("state", "PENDING")
    return getattr(slice_obj, "state", "PENDING")

@tool
def request_network_slice(
    devices: List[Dict[str, Any]], 
    slice_name: str,
    mcc: str,
    mnc: str,
    service_type: int,
    differentiator: str,
    notification_url: str,
    notification_auth_token: str,
    customer_name: str,
    customer_description: str,
    max_poll_seconds: int = 180
) -> Dict[str, Any]:
    """
    Creates, activates, and attaches devices to a 5G Network Slice.
    Polls the network lifecycle through PENDING -> AVAILABLE -> OPERATING before attaching devices.

    Args:
        devices (List[Dict[str, Any]]): List of devices with 'phone_number' (str) and 'imsi' (int/str).
        slice_name (str): Desired slice name (letters, numbers, hyphens only).
        mcc (str): Mobile Country Code (e.g., "236").
        mnc (str): Mobile Network Code (e.g., "30").
        service_type (int): SST Service type integer (e.g., 1 for eMBB).
        differentiator (str): Hex string differentiator (e.g., "000001").
        notification_url (str): HTTPS Webhook endpoint for status updates.
        notification_auth_token (str): Secret auth token for the webhook.
        customer_name (str): Customer name for slice attachment.
        customer_description (str): Reason/description for slice allocation.
        max_poll_seconds (int): Max timeout in seconds for status transition (default 180s).
    """
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9-]', '', slice_name)
        if not clean_name:
            clean_name = f"slice-{int(time.time())}"

        print(f"Creating slice '{clean_name}'...")
        my_slice = nac_client.slice.create_slice(
            name=clean_name,
            network_identifier={"mcc": mcc, "mnc": mnc},
            slice_info={"service_type": service_type, "differentiator": differentiator},
            notification_url=notification_url,
            notification_auth_token=notification_auth_token
        )
        
        slice_id = getattr(my_slice, "name", clean_name)
        current_state = _get_slice_state(my_slice)

        start_time = time.time()
        print(f"Waiting for slice '{slice_id}' to become AVAILABLE (Initial state: {current_state})...")

        while current_state != "AVAILABLE" and (time.time() - start_time) < max_poll_seconds:
            if current_state == "FAILED":
                return {"status": "FAILED", "error": f"Slice provisioning failed on 5G core for {slice_id}"}
            
            time.sleep(5)
            elapsed = int(time.time() - start_time)
            
            slice_data = nac_client.slice.get_slice(slice_id)
            current_state = _get_slice_state(slice_data)
            print(f"   [Polling {elapsed}s] State: {current_state}")

            if current_state in ["AVAILABLE", "OPERATING"]:
                break

        if current_state not in ["AVAILABLE", "OPERATING"]:
            return {
                "status": "PENDING", 
                "slice_name": slice_id, 
                "message": f"Slice provisioning still in progress after {max_poll_seconds}s."
            }

        if current_state != "OPERATING":
            print(f"Activating slice '{slice_id}'...")
            nac_client.slice.activate(slice_id)
            
            start_time = time.time()
            while current_state != "OPERATING" and (time.time() - start_time) < max_poll_seconds:
                time.sleep(5)
                elapsed = int(time.time() - start_time)
                
                slice_data = nac_client.slice.get_slice(slice_id)
                current_state = _get_slice_state(slice_data)
                print(f"   [Activation {elapsed}s] State: {current_state}")

                if current_state == "OPERATING":
                    break

        if current_state != "OPERATING":
            return {"status": "FAILED", "slice_name": slice_id, "error": "Slice failed to reach OPERATING state after activation."}

        print(f"Attaching devices to slice '{slice_id}'...")
        attached_devices = []
        for dev in devices:
            phone_number = dev.get("phone_number")
            raw_imsi = dev.get("imsi")
            imsi_val = int(raw_imsi) if raw_imsi is not None else 99999991000

            nac_client.slice.attach_device(
                device={"phone_number": phone_number, "imsi": imsi_val},
                slice_id=slice_id,
                customer={
                    "name": customer_name,
                    "description": customer_description
                },
                webhook={
                    "notification_url": notification_url,
                    "notification_auth_token": notification_auth_token
                }
            )
            attached_devices.append(phone_number)

        print(f"Slicing completed successfully!")
        return {
            "slice_name": slice_id,
            "status": "OPERATING",
            "devices_attached": attached_devices
        }

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

if __name__ == "__main__":
    unique_test_slice = f"slice-z47-{int(time.time())}"
    
    test_payload = {
        "devices": [
            {
                "phone_number": "+99999991000",
                "imsi": 236301234567890
            }
        ],
        "slice_name": unique_test_slice,
        "mcc": "236",
        "mnc": "30",
        "service_type": 1,
        "differentiator": "000001",
        "notification_url": "https://example.com/notifications",
        "notification_auth_token": "c8974e592c2fa383d4a3960714",
        "customer_name": "AquaPulse Utility System",
        "customer_description": "Emergency 5G Slice allocation for Pipe Burst Telemetry",
        "max_poll_seconds": 180
    }

    print(f"Testing Network Slicing tool with unique ID: {unique_test_slice}...\n")
    result = request_network_slice.invoke(test_payload)
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))