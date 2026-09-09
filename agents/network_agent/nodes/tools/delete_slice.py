import json
import os
from typing import Dict, Any
from langchain_core.tools import tool
from agents.network_agent.camara_api import camara_service
from dotenv import load_dotenv
from agents.network_agent.camara_api import camara_service

load_dotenv()

@tool
def delete_slice(
    phone_number: str,
    slice_id: str
) -> Dict[str, Any]:
    """
    Detaches a device from a 5G network slice after an incident is resolved.
    """
    slice_id = slice_id or os.getenv("PREPROVISIONED_SLICE_ID", "aquapulse-critical-slice")
    print(f"\n[Detach Tool] Searching attachments for phone '{phone_number}' on slice '{slice_id}'...")
    all_attachments_resp = camara_service.get_all_attachments()
    if all_attachments_resp.get("status") != "SUCCESS":
        return {
            "status": "FAILED",
            "phone_number": phone_number,
            "slice_id": slice_id,
            "error": f"Failed to retrieve attachments: {all_attachments_resp.get('error')}"
        }

    attachments = all_attachments_resp.get("attachments", [])
    def matches(att):
        try:
            return att.resource.slice_id == slice_id and att.resource.device.phone_number == phone_number
        except AttributeError:
            return False

    target_nac_resource_id = next((att.nac_resource_id for att in attachments if matches(att)), None)

    if not target_nac_resource_id:
        return {
            "status": "NOT_FOUND",
            "phone_number": phone_number,
            "slice_id": slice_id,
            "message": f"No active attachment found for device '{phone_number}' on slice '{slice_id}'."
        }
    
    print(f"[Detach Tool] Found attachment ID '{target_nac_resource_id}'. Detaching...")
    detach_result = camara_service.detach_device_from_slice(device_id=target_nac_resource_id)

    return {
        "status": detach_result.get("status"),
        "phone_number": phone_number,
        "slice_id": slice_id,
        "nac_resource_id": target_nac_resource_id,
        "response": detach_result
    }
