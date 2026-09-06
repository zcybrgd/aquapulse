"""Minimal Investigation Agent HTTP wrapper.

Copy this around an existing Python investigation module. AquaPulse expects:

  GET  /health
  GET  /v1/contract
  POST /v1/investigate

AquaPulse remains the authority for incidents. This service only returns advisory findings.
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Investigation Agent wrapper example", version="1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "agent_code": "investigation_agent",
        "schema_version": "1.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/contract")
def contract() -> dict:
    return {
        "agent_code": "investigation_agent",
        "schema_version": "1.0",
        "endpoints": ["GET /health", "GET /v1/contract", "POST /v1/investigate"],
    }


@app.post("/v1/investigate")
def investigate(payload: dict) -> JSONResponse:
    run_id = payload.get("run_id")
    batch_id = (payload.get("batch") or {}).get("batch_id") or "batch-demo"
    return JSONResponse(
        {
            "schema_version": "1.0",
            "run_id": run_id,
            "data_mode": "mock",
            "batch": {
                "batch_id": batch_id,
                "analysis_timestamp": "2026-08-31T02:00:00Z",
                "total_clusters_analyzed": 1,
                "anomalies_detected_count": 1,
                "investigated_threats": [
                    {
                        "anomaly_id": "e048d424-6a15-47ed-a35c-b3cc4c5ff445",
                        "sensor_cluster_id": "cluster-desert-042",
                        "segment_id": "seg-neom-north-01",
                        "classification": "confirmed_anomaly",
                        "severity_tier": 3,
                        "network_status": {
                            "camara_reachability_status": "REACHABLE",
                            "camara_congestion_level": "LOW",
                            "api_unavailable": False,
                        },
                        "physical_deviations": {
                            "pressure_drop_pct": 36.6071,
                            "flow_surge_pct": 40.2743,
                            "pressure_slope": -1.9033,
                            "flow_slope": 3.9317,
                            "is_stale_pre_outage_data": False,
                        },
                        "criticality_metrics": {
                            "criticality_score": 3,
                            "proximity_to_reservoir_m": 120.0,
                            "population_served": 45000,
                            "associated_valve_id": "valve-neom-north-01",
                            "pipe_diameter_mm": 400.0,
                        },
                        "operator_justification": "Operator justification text",
                        "confidence_score": 0.9078,
                    }
                ],
            },
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9001)
