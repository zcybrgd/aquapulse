from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI(title="valve-actuator-sim")

#In-memory valve state per device, so /v1/valve/status reflects real state changes across calls during the demo.
_valve_state: dict[str, str] = {}

class IsolateRequest(BaseModel):
    device_id: str
    incident_id: str
    action: str  # "close"

#a simple simulator of a physical valve controller
@app.post("/v1/valve/isolate")
def isolate(body: IsolateRequest) -> dict:
    if body.device_id.endswith("-fail"):
        return {"confirmed": False, "reason": "simulated actuator did not confirm closure"}
    _valve_state[body.device_id] = "closed"
    print(f"[VALVE] device={body.device_id} incident={body.incident_id} -> CLOSED")
    return {"confirmed": True}


@app.get("/v1/valve/status/{device_id}")
def status(device_id: str) -> dict:
    return {"device_id": device_id, "state": _valve_state.get(device_id, "open")}