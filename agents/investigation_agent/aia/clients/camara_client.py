from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from network_as_code import NetworkAsCodeApi

from .device_reachability import DeviceReachabilityClient

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="investigation-agent")


# ---------------------------------------------------------------------------
# Nokia Network-as-Code client
# ---------------------------------------------------------------------------

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
# Fail fast if the API key is missing.
# The service must never run unauthenticated.

network_client = NetworkAsCodeApi(
    rapidapi_host="network-as-code.nokia.rapidapi.com",
    api_key=RAPIDAPI_KEY,
)


# ---------------------------------------------------------------------------
# CAMARA clients
# ---------------------------------------------------------------------------

device_reachability_client = DeviceReachabilityClient(network_client)


# ---------------------------------------------------------------------------
# Device mapping
# ---------------------------------------------------------------------------
#
# The industrial application works with its own device/sensor identifiers.
# Nokia Network-as-Code expects the corresponding network identifier.
#
# Keep this mapping here for the simulated testbed. In a production
# deployment, this should normally come from the site's asset registry
# or another configuration/database layer.
# ---------------------------------------------------------------------------

DEVICE_ID_MAP: dict[str, str] = {
    "device-14-valve-A": "+99999991001",
    "device-offline-demo": "+99999991003",
    "device-14-valve-A-fail": "+99999991001",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_phone_number(device_id: str) -> str:
    """
    Resolve an industrial device ID to its Nokia Network-as-Code
    network identifier.
    """
    phone_number = DEVICE_ID_MAP.get(device_id)

    if phone_number is None:
        raise HTTPException(
            status_code=404,
            detail=f"No Nokia test-device mapping for '{device_id}'",
        )

    return phone_number


# ---------------------------------------------------------------------------
# Device Reachability Status
# ---------------------------------------------------------------------------

@app.get("/v1/device-reachability/{device_id}")
def get_device_reachability(device_id: str) -> dict:
    """
    Retrieve the connectivity status of an industrial device
    through Nokia Network-as-Code.
    """

    phone_number = get_phone_number(device_id)

    try:
        status = device_reachability_client.get_device_connectivity(
            phone_number
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Nokia NaC Device Reachability call failed: {exc}",
        ) from exc

    reachable = bool(
        getattr(status, "reachable", False)
    )

    connectivity = (
        getattr(status, "connectivity", None)
        or []
    )

    return {
        "device_id": device_id,
        "reachable": reachable,
        "signal_quality": (
            ",".join(connectivity)
            if connectivity
            else "NONE"
        ),
    }


# ---------------------------------------------------------------------------
# Congestion Insights
# ---------------------------------------------------------------------------
#
# IMPORTANT:
# The exact Nokia Network-as-Code Python SDK client/method for Congestion
# Insights depends on the SDK/API version being used.
#
# Do not implement this by making a direct httpx request: the integration
# service is intentionally based on NetworkAsCodeApi, following the
# architecture of the first script.
#
# Once the corresponding SDK client is available, initialize it above:
#
#     congestion_client = CongestionInsightsClient(network_client)
#
# and replace the implementation below with:
#
#     insights = congestion_client.get_congestion_insights(phone_number)
#
# ---------------------------------------------------------------------------

@app.get("/v1/congestion-insights/{device_id}")
def get_congestion_insights(device_id: str) -> dict:
    """
    Retrieve congestion information for an industrial device.

    The endpoint is intentionally exposed as part of the FastAPI service,
    but the actual SDK call must use the Congestion Insights client exposed
    by the installed Nokia Network-as-Code SDK version.
    """

    phone_number = get_phone_number(device_id)

    raise HTTPException(
        status_code=501,
        detail=(
            "Congestion Insights is not implemented because the installed "
            "Nokia Network-as-Code SDK client for this capability has not "
            "been verified. Configure the corresponding SDK client instead "
            "of using a direct HTTP implementation."
        ),
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
    }