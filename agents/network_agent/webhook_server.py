import time
import asyncio
from fastapi import FastAPI, BackgroundTasks, Header
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from agents.network_agent.camara_api import camara_service
from concurrent.futures import ThreadPoolExecutor
from fastapi.concurrency import run_in_threadpool
from agents.network_agent.nodes.response_dispatch import dispatch_grant_or_deny

app = FastAPI(title="AquaPulse Webhook & Lifecycle Listener")

PENDING_ATTACHMENTS: Dict[str, Dict[str, Any]] = {}

class WatcherRegistration(BaseModel):
    slice_id: str
    devices: List[Dict[str, Any]]
    customer_name: str
    customer_description: str
    notification_url: str
    notification_auth_token: str
    incident_context: List[Dict[str, Any]] = []

class SliceNotification(BaseModel):
    model_config = ConfigDict(extra="allow")
    resource: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    current_slice_state: Optional[str] = None


def _lookup_incident(incident_context: List[Dict[str, Any]], phone_number: str) -> Optional[Dict[str, Any]]:
    for entry in incident_context:
        if entry.get("phone_number") == phone_number:
            return entry
    return None

def trigger_response_agent_grant(incident_ctx: Dict[str, Any], *, slice_id: str, guarantee_type: str = "slice") -> None:
    """Build a final NetworkGrant for one incident/device and hand it to the Response Agent."""
    decision = {
        "cluster_id": incident_ctx["cluster_id"],
        "incident_id": incident_ctx["incident_id"],
        "severity_tier": incident_ctx["severity_tier"],
        "guarantee_type": guarantee_type,
        "session_id": slice_id,
        "granted_at": None,   # let the bridge default to now(); slice has no discrete grant timestamp
        "expires_at": None,
    }
    dispatch_grant_or_deny(
        decision,
        is_grant=True,
        device_id=incident_ctx["phone_number"],
    )

def trigger_response_agent_deny(incident_ctx: Dict[str, Any], *, reason: str, fallback: str = "SMS") -> None:
    decision = {
        "cluster_id": incident_ctx["cluster_id"],
        "incident_id": incident_ctx["incident_id"],
        "severity_tier": incident_ctx["severity_tier"],
        "reasoning_trace": reason,
        "fallback": fallback,
    }
    dispatch_grant_or_deny(
        decision,
        is_grant=False,
        device_id=incident_ctx["phone_number"],
    )


def _reap_slice(slice_id: str, reason: str):
    """Deletes wedged/failed slice directly to protect tenant queue."""
    print(f"  [REAP TRIGGERED] Deleting slice '{slice_id}' from network core (Reason: {reason})...")
    try:
        camara_service.delete_slice_direct(slice_id)
        print(f"  [Reap Success] Deleted wedged slice '{slice_id}'.")
    except Exception as del_err:
        print(f"  [Reap Error] Could not delete slice '{slice_id}': {del_err}")

    watcher_data = PENDING_ATTACHMENTS.get(slice_id, {})
    incident_context = watcher_data.get("incident_context", [])
    if not incident_context:
        print(f"  [Reap Warning] No incident_context for slice '{slice_id}' — cannot notify Response Agent per-incident.")
        return
    for ctx in incident_context:
        trigger_response_agent_deny(
            ctx,
            reason=f"Slice operation aborted ({reason}). Automatically reaped from core.",
            fallback="SMS",
       )


def attach_all_devices(slice_id: str, attachment_data: Dict[str, Any]) -> Dict[str, Any]:
    devices = attachment_data["devices"]
    customer_name = attachment_data["customer_name"]
    customer_description = attachment_data["customer_description"]
    notification_url = attachment_data["notification_url"]
    notification_auth_token = attachment_data["notification_auth_token"]
    incident_context = attachment_data.get("incident_context", [])

    attached_devices_info = []
    print(f"\n[Lifecycle Manager] Slice '{slice_id}' is OPERATING! Attaching {len(devices)} devices...")

    for idx, dev in enumerate(devices):
        phone_number = dev.get("phone_number")
        raw_imsi = dev.get("imsi")
        imsi_val = int(raw_imsi) if raw_imsi is not None else (99999991000 + idx)
        incident_ctx = _lookup_incident(incident_context, phone_number)

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
            if incident_ctx:
                trigger_response_agent_grant(incident_ctx, slice_id=slice_id, guarantee_type="slice")
            else:
                print(f"  [Warning] No incident_context match for {phone_number} — Response Agent not notified.")
        except Exception as attach_err:
            attached_devices_info.append({
                "phone_number": phone_number,
                "imsi": imsi_val,
                "status": f"FAILED: {attach_err}"
            })
            print(f"  [Attach Failed] {phone_number}: {attach_err}")
            if incident_ctx:
                trigger_response_agent_deny(
                    incident_ctx,
                    reason=f"Slice '{slice_id}' attach failed for device {phone_number}: {attach_err}",
                    fallback="SMS",
                )

        time.sleep(1)

    completed_payload = {
        "grant_type": "network_slicing",
        "status": "COMPLETED",
        "slice_id": slice_id,
        "customer_name": customer_name,
        "devices": attached_devices_info
    }
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
            incident_context = watcher_data.get("incident_context", [])
            for ctx in incident_context:
                trigger_response_agent_deny(
                    ctx,
                    reason=f"Slice '{slice_id}' entered terminal state '{current_state}'.",
                    fallback="SMS",
                )
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
        "activation_attempted": False,
        "incident_context": data.incident_context,
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
            # attach_all_devices does blocking network calls (attach_device x N,
            # time.sleep(1) per device, plus response-agent dispatch fan-out) —
            # must not run on the event loop.
            await run_in_threadpool(attach_all_devices, slice_id, data)


    return {"status": "ACKNOWLEDGED"}