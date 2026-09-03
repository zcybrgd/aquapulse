"""
Dashboard service.

- Serves the single-page frontend (static/index.html + app.js).
- Subscribes to Redis pub/sub channels `sim:state` and `aia:results` in a
  background task, and rebroadcasts every message to all connected browser
  WebSockets (`/ws`).
- Proxies the Scenario Control Panel's REST calls through to the simulator,
  so the browser only ever talks to this one service (no CORS setup needed
  across the internal Docker network).
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dashboard")

app = FastAPI(title="Water Pipeline Dashboard")

_connections: set[WebSocket] = set()
_http_client: httpx.AsyncClient | None = None
_pubsub_task: asyncio.Task | None = None


@app.on_event("startup")
async def on_startup():
    global _http_client, _pubsub_task
    _http_client = httpx.AsyncClient(timeout=5.0)
    _pubsub_task = asyncio.create_task(_pubsub_loop())


@app.on_event("shutdown")
async def on_shutdown():
    if _pubsub_task:
        _pubsub_task.cancel()
    if _http_client:
        await _http_client.aclose()


async def _pubsub_loop() -> None:
    while True:
        try:
            redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=True)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("sim:state", "sim:raw_logs", "aia:results")
            logger.info("Subscribed to sim:state, sim:raw_logs, and aia:results")
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                await _broadcast(message["data"])
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Redis pubsub loop error; retrying in 3s")
            await asyncio.sleep(3)


async def _broadcast(raw_message: str) -> None:
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(raw_message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.discard(ws)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            # Frontend doesn't send anything meaningful; just keep the socket alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)


# ---------------------------------------------------------------------------
# Control panel proxy -> simulator
# ---------------------------------------------------------------------------

async def _proxy(method: str, path: str, json_body: dict | None = None):
    assert _http_client is not None
    resp = await _http_client.request(method, f"{config.SIMULATOR_URL}{path}", json=json_body)
    return resp.json(), resp.status_code


@app.get("/api/state")
async def api_state():
    data, status = await _proxy("GET", "/state")
    return data


@app.get("/api/topology")
async def api_topology():
    data, status = await _proxy("GET", "/topology")
    return data


@app.get("/api/faults/catalog")
async def api_faults_catalog():
    data, status = await _proxy("GET", "/faults/catalog")
    return data


@app.post("/api/control/start")
async def api_start():
    data, status = await _proxy("POST", "/control/start")
    return data


@app.post("/api/control/stop")
async def api_stop():
    data, status = await _proxy("POST", "/control/stop")
    return data


@app.post("/api/control/reset")
async def api_reset():
    data, status = await _proxy("POST", "/control/reset")
    return data


@app.post("/api/control/inject_fault")
async def api_inject_fault(body: dict):
    data, status = await _proxy("POST", "/control/inject_fault", body)
    return JSONResponse(content=data, status_code=status)


@app.post("/api/control/clear_fault/{cluster_id}")
async def api_clear_fault(cluster_id: str):
    data, status = await _proxy("POST", f"/control/clear_fault/{cluster_id}")
    return data


@app.post("/api/control/clear_all_faults")
async def api_clear_all():
    data, status = await _proxy("POST", "/control/clear_all_faults")
    return data


@app.post("/api/control/simulate_api_outage/{cluster_id}")
async def api_simulate_api_outage(cluster_id: str):
    data, status = await _proxy("POST", f"/control/simulate_api_outage/{cluster_id}")
    return data


@app.post("/api/control/clear_api_outage/{cluster_id}")
async def api_clear_api_outage(cluster_id: str):
    data, status = await _proxy("POST", f"/control/clear_api_outage/{cluster_id}")
    return data


@app.post("/api/control/set_temperature")
async def api_set_temp(body: dict):
    data, status = await _proxy("POST", "/control/set_temperature", body)
    return data


@app.get("/api/results/latest/{cluster_id}")
async def api_latest_result(cluster_id: str):
    assert _http_client is not None
    resp = await _http_client.get(f"{config.AIA_SERVICE_URL}/results/latest/{cluster_id}")
    if resp.status_code == 404:
        return {}
    return resp.json()


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")
