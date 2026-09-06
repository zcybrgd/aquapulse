"""Minimal Response Agent HTTP wrapper.

Copy this around an existing Python response module. AquaPulse expects:

  GET  /health
  GET  /v1/contract
  POST /v1/recommend-response

The path is recommend-response, not execute. AquaPulse owns actuation.
If the existing graph exposes another path, configure RESPONSE_AGENT_RECOMMEND_PATH.
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Response Agent wrapper example", version="1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "agent_code": "response_agent",
        "schema_version": "1.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/contract")
def contract() -> dict:
    return {
        "agent_code": "response_agent",
        "schema_version": "1.0",
        "endpoints": ["GET /health", "GET /v1/contract", "POST /v1/recommend-response"],
    }


@app.post("/v1/recommend-response")
def recommend(payload: dict) -> JSONResponse:
    return JSONResponse(
        {
            "schema_version": "1.0",
            "result_id": f"res-{payload.get('run_id', 'demo')}",
            "incident_id": payload.get("incident_id", "INC-1835"),
            "cluster_id": payload.get("cluster_id", "AP-CLUSTER-DET-000001"),
            "device_id": payload.get("device_id", "VLV-HBR-007"),
            "severity_tier": payload.get("severity_tier", 2),
            "reachability": {"status": "REACHABLE"},
            "decision": "ALERT_AND_AWAIT",
            "notification_sent": False,
            "valve_command_sent": False,
            "valve_command_confirmed": False,
            "human_override_requested": True,
            "human_override_response": None,
            "reasoning_trace": [{"step": "reachability_check"}, {"step": "llm_response_planner"}],
            "created_at": "2026-09-01T07:45:00Z",
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9002)
