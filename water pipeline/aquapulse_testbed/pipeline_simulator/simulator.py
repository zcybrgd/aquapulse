import os
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AquaPulse Water Pipeline Simulator & Mock CAMARA API")

# Global State
class PipelineState:
    def __init__(self):
        self.scenario = "normal"  # "normal", "burst", "instrument_fault", "thermal_outage"
        self.valve_state = "OPEN" # "OPEN", "CLOSED"
        self.ambient_temp = 48.0
        self.reachability = "REACHABLE"
        self.congestion = "LOW"
        self.pressure = 45.0
        self.flow_rate = 80.0

state = PipelineState()

class ScenarioRequest(BaseModel):
    scenario: str

class ValveRequest(BaseModel):
    valve_id: str
    state: str

@app.get("/state")
def get_state():
    # Dynamically update telemetry based on scenario and valve state
    if state.valve_state == "CLOSED":
        state.pressure = 0.0
        state.flow_rate = 0.0
    else:
        if state.scenario == "normal":
            state.ambient_temp = 48.0 + random.normalvariate(0, 0.5)
            state.flow_rate = 80.0 + random.normalvariate(0, 1.0)
            state.pressure = 45.0 - 0.1 * (state.flow_rate - 80.0) + random.normalvariate(0, 0.2)
            state.reachability = "REACHABLE"
            state.congestion = "LOW"
        elif state.scenario == "burst":
            state.ambient_temp = 48.0 + random.normalvariate(0, 0.5)
            state.flow_rate = 112.5 + random.normalvariate(0, 1.5)
            state.pressure = 28.4 + random.normalvariate(0, 0.4)
            state.reachability = "REACHABLE"
            state.congestion = "LOW"
        elif state.scenario == "instrument_fault":
            state.ambient_temp = 45.0 + random.normalvariate(0, 0.5)
            state.flow_rate = 0.0
            state.pressure = 0.0
            state.reachability = "UNREACHABLE"
            state.congestion = "LOW"
        elif state.scenario == "thermal_outage":
            state.ambient_temp = 51.5 + random.normalvariate(0, 0.3)
            # Hydralics are actually normal, but telemetry fails
            state.flow_rate = 80.0 + random.normalvariate(0, 1.0)
            state.pressure = 45.0 + random.normalvariate(0, 0.2)
            state.reachability = "UNREACHABLE"
            state.congestion = "HIGH"

    return {
        "scenario": state.scenario,
        "valve_state": state.valve_state,
        "ambient_temp_c": round(state.ambient_temp, 2),
        "pressure_psi": round(state.pressure, 2),
        "flow_rate_lps": round(state.flow_rate, 2),
        "reachability": state.reachability,
        "congestion": state.congestion
    }

@app.post("/set-scenario")
def set_scenario(req: ScenarioRequest):
    if req.scenario not in ["normal", "burst", "instrument_fault", "thermal_outage"]:
        raise HTTPException(status_code=400, detail="Invalid scenario")
    state.scenario = req.scenario
    if req.scenario == "normal":
        state.valve_state = "OPEN"
    return {"status": "success", "scenario": state.scenario}

@app.post("/control-valve")
def control_valve(req: ValveRequest):
    if req.state not in ["OPEN", "CLOSED"]:
        raise HTTPException(status_code=400, detail="Invalid valve state")
    state.valve_state = req.state
    return {"status": "success", "valve_id": req.valve_id, "state": state.valve_state}

# Mock CAMARA APIs
@app.get("/camara/device-reachability-status/v1")
def get_reachability(device_id: str):
    # Simulate API response based on current state
    return {
        "device_id": device_id,
        "reachability_status": state.reachability
    }

@app.get("/camara/congestion-insights/v1")
def get_congestion(device_id: str):
    return {
        "device_id": device_id,
        "congestion_level": state.congestion
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
