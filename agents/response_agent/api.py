"""Readiness HTTP surface for the Response Agent.

AquaPulse probes GET /health and GET /v1/contract only. Execution stays
outside AquaPulse; this app does not expose recommend/execute routes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="AquaPulse Response Agent", version="1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "response_agent",
        "agent_code": "response_agent",
        "schema_version": "1.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/contract")
def contract() -> dict:
    return {
        "agent_name": "response_agent",
        "agent_code": "response_agent",
        "contract_version": "1.0",
        "schema_version": "1.0",
        "endpoints": ["GET /health", "GET /v1/contract"],
    }
