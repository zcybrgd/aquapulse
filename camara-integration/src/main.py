from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from network_as_code import NetworkAsCodeApi
from clients.device_reachability import DeviceReachabilityClient
from clients.qod import QodClient

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="camara-integration")

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]  
network_client = NetworkAsCodeApi(rapidapi_host="network-as-code.nokia.rapidapi.com",api_key=RAPIDAPI_KEY,)
device_reachability_client = DeviceReachabilityClient(network_client)
qod_client = QodClient(network_client)

DEVICE_ID_MAP: dict[str, str] = {
    "device-14-valve-A": "+99999991001",       # simulated: has a data connection
    "device-offline-demo": "+99999991003",     # simulated: has lost connectivity
    "device-14-valve-A-fail": "+99999991001",  # reachable; actuator sim forces the failure downstream
}

def get_phone_number(device_id: str) -> str:
    phone_number = DEVICE_ID_MAP.get(device_id)
    if phone_number is None:
        raise HTTPException(status_code=404, detail=f"No Nokia test-device mapping for '{device_id}'")
    return phone_number


@app.get("/v1/device-reachability/{device_id}")
def get_device_reachability(device_id: str) -> dict:
    phone_number = get_phone_number(device_id)
    try:
        status = device_reachability_client.get_device_connectivity(phone_number)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Nokia NaC call failed: {exc}") from exc

    reachable = bool(getattr(status, "reachable", False))
    connectivity = getattr(status, "connectivity", None) or []
    return { "reachable": reachable,"signal_quality": ",".join(connectivity) if connectivity else "NONE",}

@app.post("/v1/qod/{device_id}/reserve")
def reserve_qod_session(device_id: str, application_server_ip: str, duration_seconds: int = 3600) -> dict:
    phone_number = get_phone_number(device_id)
    try:
        session = qod_client.reserve_session(phone_number, application_server_ip, duration_seconds)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Nokia NaC QoD call failed: {exc}") from exc

    return {"session_id": session.id, "status": getattr(session, "status", None)}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}