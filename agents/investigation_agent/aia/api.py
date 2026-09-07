# agents/investigation_agent/aia/api.py
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import your agent pipeline runner
# from aia.pipeline import run_investigation_pipeline

app = FastAPI(title="AquaPulse Anomaly Investigation Agent Wrapper", version="1.0.0")

class InvestigateRequest(BaseModel):
    batch_id: str | None = None
    detections: List[Dict[str, Any]] = []

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "investigation_agent"}

@app.get("/v1/contract")
def get_contract():
    return {
        "agent_name": "investigation_agent",
        "contract_version": "1.0",
        "supported_classifications": ["confirmed_anomaly", "confirmed_instrument_fault"],
        "endpoints": {
            "health": "/health",
            "contract": "/v1/contract",
            "investigate": "/v1/investigate"
        }
    }

# Import your actual pipeline execution logic
from aia.pipeline import run_investigation_pipeline  # Adjust path as needed

@app.post("/v1/investigate")
def investigate(payload: Dict[str, Any]):
    try:
        # Execute your agent model/graph using input from `payload`
        raw_results = run_investigation_pipeline(payload)

        # Return formatted dict ensuring types match contract v1:
        # - severity_tier: int
        # - network_status: dict (with camara_reachability_status, camara_congestion_level, api_unavailable)
        return raw_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))