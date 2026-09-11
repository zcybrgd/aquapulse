import os
import time
import json
import secrets
from dotenv import load_dotenv
import pytest

from agents.network_agent.nodes.tools.request_slicing import normalize_device, request_network_slice


def test_normalize_device_maps_cluster_alias_and_uses_numeric_fallback_imsi():
    phone_number, imsi = normalize_device(
        {"phone_number": "cluster-desert-044", "imsi": "cluster-desert-044"},
        idx=0,
    )

    assert phone_number == "+99999991000"
    assert imsi == 99999991000


def test_normalize_device_rejects_unrelated_non_numeric_imsi():
    with pytest.raises(ValueError, match="expected a numeric IMSI"):
        normalize_device(
            {"phone_number": "+99999991000", "imsi": "not-an-imsi"},
            idx=0,
        )

load_dotenv()

def generate_test_devices(count: int, session_id: int) -> list:
    """Generates non-colliding device test identities derived from the session ID."""
    devices = []
    for idx in range(count):
        unique_imsi = 236301000000000 + (session_id * 100) + idx
        unique_phone = f"+999999{session_id:03d}{idx:02d}"
        devices.append({
            "phone_number": unique_phone,
            "imsi": unique_imsi
        })
    return devices

def generate_test_differentiator(session_id: int) -> str:
    """Generates a valid 6-character uppercase hex SD derived from the session ID."""
    return f"{session_id:06X}"

if __name__ == "__main__":

    mcc, mnc, service_type = "236", "30", 1
    session_id = secrets.randbelow(0xFFFFFF - 1000) + 1000  # Unique integer per run
    
    test_devices = generate_test_devices(count=2, session_id=session_id)
    differentiator = generate_test_differentiator(session_id)  # e.g., '001A3F'

    # 3. Build test payload
    test_payload = {
        "devices": test_devices,
        "slice_name": f"slice-test-{session_id}-{int(time.time())}",
        "mcc": mcc,
        "mnc": mnc,
        "service_type": service_type,
        "differentiator": differentiator,
        "customer_name": "AquaPulse System Test",
        "customer_description": "Testing Async Webhook Slicing Flow"
    }

    print("================ 1. INVOKING TOOL ================")
    print(f"Session ID:     {session_id}")
    print(f"Slice Name:     {test_payload['slice_name']}")
    print(f"Differentiator: {differentiator}")
    print(f"Devices:        {json.dumps(test_payload['devices'])}")

    start_time = time.time()
    
    # Execute tool call
    response = request_network_slice.invoke(test_payload)
    
    elapsed = time.time() - start_time
    print(f"\n[Tool Returned Control to Agent in {elapsed:.2f} seconds]")
    print(json.dumps(response, indent=2))
    
    print("\n================ 2. WAITING FOR WEBHOOKS ================")
    print("Keep this terminal open and watch your Uvicorn terminal for incoming state transitions.")