"""
aia_service: a thin FastAPI wrapper around the already-built Anomaly
Investigation Agent (`aia` package, copied in unmodified).

POST /batches receives a StreamingBatch-shaped JSON payload from the
simulator, validates it against the AIA's own Pydantic schema, runs
`AnomalyInvestigationAgent.process_batch()`, persists the results to
TimescaleDB, publishes them to Redis (`aia:results`) for the dashboard, and
returns the validated `AIABatchOutputPayload` JSON.
"""
from __future__ import annotations

import json
import logging

import redis as sync_redis
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

import config
import db
from agent_factory import build_agent

from aia.models import StreamingBatch

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("aia_service")

agent = build_agent()
app = FastAPI(title="AIA Service")

# A small sync Redis connection pool, safe to use from FastAPI's threadpool-executed
# `def` handlers (see /batches below) without any async/sync bridging.
_redis_pool = sync_redis.ConnectionPool.from_url(config.REDIS_URL, decode_responses=True)


@app.on_event("startup")
def on_startup():
    db.init_db()
    logger.info(
        "aia_service ready (LLM narration: %s)",
        "enabled" if config.ANTHROPIC_API_KEY else "deterministic fallback",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/batches")
def process_batch(raw_batch: dict):
    """
    Synchronous endpoint (FastAPI/Starlette runs `def` handlers in a
    threadpool) since the AIA pipeline and the SimulatedCamaraClient it
    calls are both synchronous HTTP calls, not asyncio coroutines.
    """
    try:
        batch = StreamingBatch.model_validate(raw_batch)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc

    payload = agent.process_batch(batch)
    payload_dict = payload.model_dump(mode="json")

    db.record_batch(payload.batch_id, payload.total_clusters_analyzed, payload.anomalies_detected_count)
    db.record_results(payload.batch_id, payload_dict["investigated_threats"])

    if payload_dict["investigated_threats"]:
        try:
            client = sync_redis.Redis(connection_pool=_redis_pool)
            client.publish("aia:results", json.dumps({"type": "aia_results", **payload_dict}))
        except Exception:
            logger.exception("Failed to publish AIA results to redis")

    return payload_dict


@app.get("/results/latest/{cluster_id}")
async def latest_result(cluster_id: str):
    result = db.latest_result_for_cluster(cluster_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No results yet for this cluster")
    return result
