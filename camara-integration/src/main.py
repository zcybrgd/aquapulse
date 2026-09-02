from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import FastAPI, HTTPException
from network_as_code import NetworkAsCodeApi

app = FastAPI(title="camara-integration")
RESPONSE_AGENT_CAMARA_API_KEY= os.environ.get("RESPONSE_AGENT_CAMARA_API_KEY")
client = NetworkAsCodeApi(rapidapi_host="network-as-code.nokia.rapidapi.com",api_key=RESPONSE_AGENT_CAMARA_API_KEY,)

DEVICE_ID_MAP: dict[str, str] = {"device-14-valve-A": "+99999991001",  # simulated: has a data connection
"device-offline-demo": "+99999991003",  # simulated: has lost connectivity
}


def resolve_phone_number(device_id: str) -> str:
    phone_number = DEVICE_ID_MAP.get(device_id)
    if phone_number is None:
        raise HTTPException(status_code=404, detail=f"No Nokia test-device mapping for '{device_id}'")
    return phone_number


@app.get("/v1/device-reachability/{device_id}")
def get_device_reachability(device_id: str) -> dict:
    phone_number = resolve_phone_number(device_id)
    try:
        status = client.device_status.retrieve_reachability_status(device={"phone_number": phone_number},)
    except Exception as exc:  # Nokia SDK errors aren't finely typed in early versions
        raise HTTPException(status_code=502, detail=f"Nokia NaC call failed: {exc}") from exc
    return { "reachable": bool(status.get("reachable", False)),
    "signal_quality": ",".join(status.get("connectivity", [])) or None,}