"""
Simulator service.

Responsibilities:
  - Runs the physics tick loop as a background asyncio task.
  - Exposes a Scenario Control Panel API: start/stop/reset, inject/clear
    faults, set environment temperature, list available fault types.
  - Every `BATCH_INTERVAL_TICKS`, builds a StreamingBatch and POSTs it to
    `aia_service`.
  - Exposes `/network_status/{cluster_id}`, consumed by aia_service's
    `SimulatedCamaraClient` to stand in for the real Nokia NaC CAMARA APIs.
  - Publishes live cluster state + fault events to Redis pub/sub
    (`sim:state`) so the dashboard can render everything in real time.
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from faults import build_fault, list_available_faults
from network_sim import derive_network_state
from physics import SimulationState, tick
from telemetry import build_batch
from topology import SEGMENTS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("simulator")

state = SimulationState(tick_seconds=config.TICK_SECONDS)
_redis: aioredis.Redis | None = None
_http_client: httpx.AsyncClient | None = None
_background_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _http_client, _background_task
    _redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    _http_client = httpx.AsyncClient(timeout=5.0)
    state.running = True
    _background_task = asyncio.create_task(_run_loop())
    logger.info("Simulator started. Clusters: %s", list(state.clusters.keys()))
    yield
    state.running = False
    if _background_task:
        _background_task.cancel()
    await _http_client.aclose()
    await _redis.aclose()


app = FastAPI(title="Water Pipeline Simulator", lifespan=lifespan)


async def _run_loop() -> None:
    tick_index = 0
    while True:
        try:
            if state.running:
                tick(state)
                tick_index += 1
                await _publish_state()
                if tick_index % config.BATCH_INTERVAL_TICKS == 0:
                    await _dispatch_batch()
            await asyncio.sleep(state.tick_seconds)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in simulation tick loop")
            await asyncio.sleep(state.tick_seconds)


async def _publish_state() -> None:
    if _redis is None:
        return
    payload = {
        "type": "sim_state",
        "tick": state.tick_count,
        "environment_temp_c": round(state.environment_temp_c, 1),
        "clusters": {
            cid: {
                "pressure_psi": c.reported_pressure_psi,
                "flow_rate_lps": c.reported_flow_lps,
                "ambient_temp_c": c.ambient_temp_c,
                "active_fault": state.active_faults[cid].fault_type if cid in state.active_faults else None,
                "magnitude": state.active_faults[cid].magnitude if cid in state.active_faults else None,
            }
            for cid, c in state.clusters.items()
        },
        "recent_events": state.fault_event_log[:10],
    }
    try:
        await _redis.publish("sim:state", json.dumps(payload))
    except Exception:
        logger.exception("Failed to publish sim state to redis")


async def _dispatch_batch() -> None:
    batch = build_batch(state)
    if not batch["telemetry_windows"]:
        return
    if _redis is not None:
        try:
            await _redis.publish("sim:telemetry", json.dumps(batch))
        except Exception:
            logger.exception("Failed to publish telemetry batch to redis")
    if _http_client is None:
        return
    try:
        resp = await _http_client.post(f"{config.AIA_SERVICE_URL}/batches", json=batch)
        if resp.status_code >= 400:
            logger.warning("aia-service rejected batch %s: %s", batch["batch_id"], resp.text[:300])
    except Exception:
        logger.exception("Failed to dispatch batch to aia-service")


# ---------------------------------------------------------------------------
# Control API
# ---------------------------------------------------------------------------

class InjectFaultRequest(BaseModel):
    cluster_id: str
    fault_type: str
    magnitude: str = "default"


class SetTempRequest(BaseModel):
    preset: str | None = None
    value_c: float | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "running": state.running, "tick": state.tick_count}


@app.get("/topology")
async def topology():
    return {"segments": SEGMENTS}


@app.get("/faults/catalog")
async def faults_catalog():
    return list_available_faults()


@app.post("/control/start")
async def start():
    state.running = True
    return {"running": True}


@app.post("/control/stop")
async def stop():
    state.running = False
    return {"running": False}


@app.post("/control/reset")
async def reset():
    state.reset()
    return {"status": "reset", "tick": state.tick_count}


@app.post("/control/inject_fault")
async def inject_fault(req: InjectFaultRequest):
    if req.cluster_id not in state.clusters:
        raise HTTPException(status_code=404, detail=f"Unknown cluster_id '{req.cluster_id}'")
    if req.cluster_id in state.active_faults:
        raise HTTPException(
            status_code=409,
            detail=f"Cluster '{req.cluster_id}' already has an active fault; clear it first.",
        )
    try:
        fault = build_fault(req.fault_type, req.magnitude, req.cluster_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state.inject_fault(fault)
    return {
        "status": "injected",
        "cluster_id": req.cluster_id,
        "fault_type": req.fault_type,
        "magnitude": req.magnitude,
        "description": fault.effect.description,
    }


@app.post("/control/clear_fault/{cluster_id}")
async def clear_fault(cluster_id: str):
    cleared = state.clear_fault(cluster_id)
    if not cleared:
        raise HTTPException(status_code=404, detail=f"No active fault on '{cluster_id}'")
    return {"status": "cleared", "cluster_id": cluster_id}


@app.post("/control/clear_all_faults")
async def clear_all_faults():
    state.clear_all_faults()
    return {"status": "cleared_all"}


@app.post("/control/simulate_api_outage/{cluster_id}")
async def simulate_api_outage(cluster_id: str):
    """Simulates the Nokia NaC CAMARA platform itself going down for this cluster."""
    if cluster_id not in state.clusters:
        raise HTTPException(status_code=404, detail=f"Unknown cluster_id '{cluster_id}'")
    state.set_api_outage(cluster_id, True)
    return {"status": "api_outage_simulated", "cluster_id": cluster_id}


@app.post("/control/clear_api_outage/{cluster_id}")
async def clear_api_outage(cluster_id: str):
    if cluster_id not in state.clusters:
        raise HTTPException(status_code=404, detail=f"Unknown cluster_id '{cluster_id}'")
    state.set_api_outage(cluster_id, False)
    return {"status": "api_outage_cleared", "cluster_id": cluster_id}


@app.post("/control/set_temperature")
async def set_temperature(req: SetTempRequest):
    try:
        value = req.preset if req.preset is not None else req.value_c
        if value is None:
            raise HTTPException(status_code=400, detail="Provide either 'preset' or 'value_c'")
        new_temp = state.set_environment_temp(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"environment_temp_c": new_temp}


@app.get("/state")
async def get_state():
    return {
        "tick": state.tick_count,
        "running": state.running,
        "environment_temp_c": state.environment_temp_c,
        "clusters": {
            cid: {
                "true_pressure_psi": round(c.true_pressure_psi, 2),
                "reported_pressure_psi": round(c.reported_pressure_psi, 2),
                "true_flow_lps": round(c.true_flow_lps, 2),
                "reported_flow_lps": round(c.reported_flow_lps, 2),
                "ambient_temp_c": round(c.ambient_temp_c, 2),
                "window_len": len(state.windows[cid]),
                "active_fault": (
                    {"fault_type": f.fault_type, "magnitude": f.magnitude, "description": f.effect.description}
                    if (f := state.active_faults.get(cid))
                    else None
                ),
            }
            for cid, c in state.clusters.items()
        },
        "recent_events": state.fault_event_log[:20],
    }


@app.get("/network_status/{cluster_id}")
async def network_status(cluster_id: str):
    """Consumed by aia_service's SimulatedCamaraClient in place of live Nokia NaC CAMARA APIs."""
    if cluster_id not in state.clusters:
        raise HTTPException(status_code=404, detail=f"Unknown cluster_id '{cluster_id}'")
    if cluster_id in state.api_outage_clusters:
        # Simulated platform failure -- the caller's HTTP client should treat
        # this as an exception, exercising the AIA's api_unavailable path.
        raise HTTPException(status_code=503, detail="Simulated Nokia NaC platform outage")
    cluster = state.clusters[cluster_id]
    fault = state.active_faults.get(cluster_id)
    net = derive_network_state(cluster.ambient_temp_c, fault, state.rng)
    return net
