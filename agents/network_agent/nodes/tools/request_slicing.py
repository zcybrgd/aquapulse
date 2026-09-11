import json
import os
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv
from agents.network_agent.camara_api import camara_service

load_dotenv()

CLUSTER_MSISDN_MAP: dict[str, str] = {
    "cluster-desert-042": "+99999991000",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991000",
    "cluster-desert-045": "+99999990404",
    "cluster-desert-046": "+99999991000",
}


def normalize_device(dev: Dict[str, Any], idx: int) -> tuple[str, int]:
    device_identifier = dev.get("phone_number") or dev.get("device_id")
    if not device_identifier:
        raise ValueError("Each slicing device must include phone_number or device_id.")

    phone_number = CLUSTER_MSISDN_MAP.get(device_identifier, device_identifier)
    raw_imsi = dev.get("imsi")

    if raw_imsi is None or raw_imsi == device_identifier or raw_imsi in CLUSTER_MSISDN_MAP:
        imsi_val = 99999991000 + idx
    else:
        try:
            imsi_val = int(raw_imsi)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid IMSI for device '{device_identifier}': expected a numeric IMSI, got {raw_imsi!r}."
            ) from exc

    return phone_number, imsi_val


@tool
def request_network_slice(
    devices: List[Dict[str, Any]], 
    slice_id: Optional[str] = None,
    customer_name: str = "AquaPulse Customer",
    customer_description: str = "Emergency Device Slice Attachment",
) -> Dict[str, Any]:
    """
    Attaches devices to a pre-provisioned 5G network slice and dispatches grant/deny events for each device.
    Args:
        devices (List[Dict[str, Any]]): List of devices with 'phone_number' (str) and 'imsi' (int/str)
    """
    active_slice_id = slice_id or os.getenv("PREPROVISIONED_SLICE_ID", "slice-z47-1788620730")
    attached_devices_info = []

    print(f"\n[Request Slicing Tool] Attaching {len(devices)} device(s) individually to slice '{active_slice_id}'...")

    for idx, dev in enumerate(devices):
        phone_number, imsi_val = normalize_device(dev, idx)
        
        device_payload = {
            "phone_number": phone_number,
            "imsi": imsi_val
        }
        
        try:
            attachment = camara_service.attach_device_to_slice(
                slice_id=active_slice_id,
                device=device_payload,
                customer_name=customer_name,
                customer_description=customer_description
            )
            
            nac_id = getattr(attachment, "nac_resource_id", "ATTACHED") if not isinstance(attachment, dict) else attachment.get("nac_resource_id", "ATTACHED")

            attached_devices_info.append({
                "phone_number": phone_number,
                "imsi": imsi_val,
                "nac_resource_id": nac_id,
                "status": "ATTACHED"
            })
            print(f"[Attached] {phone_number} -> Slice: {active_slice_id} (ID: {nac_id})")


        except Exception as attach_err:
            attached_devices_info.append({
                "phone_number": phone_number,
                "imsi": imsi_val,
                "status": f"FAILED: {attach_err}"
            })
            print(f"[Attach Failed] {phone_number}: {attach_err}")

    return {
        "status": "COMPLETED",
        "grant_type": "network_slicing",
        "slice_id": active_slice_id,
        "devices": attached_devices_info,
        "message": f"Processed attachment for {len(attached_devices_info)} device(s) on slice '{active_slice_id}'."
    }