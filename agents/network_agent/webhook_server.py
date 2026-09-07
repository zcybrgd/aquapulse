import time
import asyncio
from fastapi import FastAPI, BackgroundTasks, Header
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from agents.network_agent.camara_api import camara_service

app = FastAPI(title="AquaPulse Webhook & Lifecycle Listener")

PENDING_ATTACHMENTS: Dict[str, Dict[str, Any]] = {}

class WatcherRegistration(BaseModel):
    slice_id: str
    devices: List[Dict[str, Any]]
    customer_name: str
    customer_description: str
    notification_url: str
    notification_auth_token: str

class SliceNotification(BaseModel):
    model_config = ConfigDict(extra="allow")
    resource: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    current_slice_state: Optional[str] = None


def trigger_response_agent(event_data: Dict[str, Any]):
    print(f"\n[Agent Trigger] Event payload delivered to Response Agent:")
    print(event_data)


def _reap_slice(slice_id: str, reason: str):
    """Deletes wedged/failed slice directly to protect tenant queue."""
    print(f"  [REAP TRIGGERED] Deleting slice '{slice_id}' from network core (Reason: {reason})...")
    try:
        camara_service.delete_slice_direct(slice_id)
        print(f"  [Reap Success] Deleted wedged slice '{slice_id}'.")
    except Exception as del_err:
        print(f"  [Reap Error] Could not delete slice '{slice_id}': {del_err}")

    trigger_response_agent({
        "grant_type": "network_slicing",
        "status": "FAILED",
        "slice_id": slice_id,
        "error": f"Slice operation aborted ({reason}). Automatically reaped from core."
    })


def attach_all_devices(slice_id: str, attachment_data: Dict[str, Any]) -> Dict[str, Any]:
    devices = attachment_data["devices"]
    customer_name = attachment_data["customer_name"]
    customer_description = attachment_data["customer_description"]
    notification_url = attachment_data["notification_url"]
    notification_auth_token = attachment_data["notification_auth_token"]

    attached_devices_info = []
    print(f"\n[Lifecycle Manager] Slice '{slice_id}' is OPERATING! Attaching {len(devices)} devices...")

    for idx, dev in enumerate(devices):
        phone_number = dev.get("phone_number")
        raw_imsi = dev.get("imsi")
        imsi_val = int(raw_imsi) if raw_imsi is not None else (99999991000 + idx)

        try:
            camara_service.client.slice.attach_device(
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
            attached_devices_info.append({
                "phone_number": phone_number,
                "imsi": imsi_val,
                "status": "ATTACHED"
            })
            print(f"  [Device Attached] {phone_number} (IMSI: {imsi_val})")
        except Exception as attach_err:
            attached_devices_info.append({
                "phone_number": phone_number,
                "imsi": imsi_val,
                "status": f"FAILED: {attach_err}"
            })
            print(f"  [Attach Failed] {phone_number}: {attach_err}")

        time.sleep(1)

    completed_payload = {
        "grant_type": "network_slicing",
        "status": "COMPLETED",
        "slice_id": slice_id,
        "customer_name": customer_name,
        "devices": attached_devices_info
    }

    trigger_response_agent(completed_payload)
    return completed_payload


def monitor_slice_lifecycle(
    slice_id: str,
    watcher_data: Dict[str, Any],
    pending_timeout_seconds: int = 200
):
    pending_start_time = time.time()

    print(f"[Background Watcher] Started monitoring slice '{slice_id}'...")

    while True:
        try:
            my_slice = camara_service.client.slice.get_slice(slice_id)
            current_state = getattr(my_slice, "state", None) or (
                my_slice.get("state") if isinstance(my_slice, dict) else "UNKNOWN"
            )
        except Exception as e:
            print(f"  [Slice State Poll Error: '{slice_id}']: {e}")
            time.sleep(5)
            continue

        print(f"  [Slice State Poll: '{slice_id}'] -> {current_state}")

        if current_state == "PENDING":
            elapsed_pending = time.time() - pending_start_time
            if elapsed_pending > pending_timeout_seconds:
                print(f"  [REAP TRIGGERED] Slice '{slice_id}' stuck in PENDING for over {pending_timeout_seconds}s.")
                _reap_slice(slice_id, f"Timed out after {pending_timeout_seconds}s in PENDING state")
                return

        elif current_state == "AVAILABLE":
            if not watcher_data.get("activation_attempted", False):
                watcher_data["activation_attempted"] = True
                print(f"  [Slice '{slice_id}'] is AVAILABLE. Triggering single activation request...")
                try:
                    my_slice.activate()
                    print(f"  [Activation Call Sent] Order submitted. Waiting for OPERATING state...")
                except Exception as act_err:
                    print(f"  [Activation Call Warning]: {act_err}. Service order likely already in progress. Continuing poll...")

        elif current_state == "OPERATING":
            print(f"  [Slice '{slice_id}'] reached OPERATING state successfully!")
            if slice_id in PENDING_ATTACHMENTS:
                PENDING_ATTACHMENTS.pop(slice_id, None)
                attach_all_devices(slice_id, watcher_data)
            return

        elif current_state in ["FAILED", "DELETED", "REJECTED"]:
            print(f"  [Slice '{slice_id}'] entered terminal state '{current_state}'. Aborting.")
            trigger_response_agent({
                "grant_type": "network_slicing",
                "status": "FAILED",
                "slice_id": slice_id,
                "error": f"Slice entered state {current_state}"
            })
            return

        time.sleep(5)


@app.post("/register-slice-watcher")
async def register_watcher(data: WatcherRegistration, background_tasks: BackgroundTasks):
    watcher_data = {
        "devices": data.devices,
        "customer_name": data.customer_name,
        "customer_description": data.customer_description,
        "notification_url": data.notification_url,
        "notification_auth_token": data.notification_auth_token,
        "activation_attempted": False
    }
    PENDING_ATTACHMENTS[data.slice_id] = watcher_data
    
    background_tasks.add_task(monitor_slice_lifecycle, data.slice_id, watcher_data)
    return {"status": "WATCHER_REGISTERED", "slice_id": data.slice_id}


@app.post("/notifications")
async def receive_slice_notification(
    notification: SliceNotification,
    authorization: Optional[str] = Header(None)
):
    slice_id = notification.resource
    state = notification.current_slice_state

    if not slice_id or not state:
        return {"status": "ACKNOWLEDGED", "message": "Ignored non-slice state event"}

    print(f"\n[Webhook Received] Slice: '{slice_id}' | State: {state}")

    attachment_data = PENDING_ATTACHMENTS.get(slice_id)

    if state == "AVAILABLE":
        if attachment_data and not attachment_data.get("activation_attempted", False):
            attachment_data["activation_attempted"] = True
            try:
                my_slice = camara_service.client.slice.get_slice(slice_id)
                my_slice.activate()
                print(f"  [Webhook Activation] Single activation call sent for slice '{slice_id}'.")
            except Exception as e:
                print(f"  [Webhook Notice] Activation request notice: {e}")

    elif state == "OPERATING":
        data = PENDING_ATTACHMENTS.pop(slice_id, None)
        if data:
            attach_all_devices(slice_id, data)

    return {"status": "ACKNOWLEDGED"}