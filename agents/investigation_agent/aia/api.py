"""
AquaPulse AIA Agent - Unified Service
======================================
1. Listens continuously to Redis telemetry on 'sim:telemetry'.
2. Runs telemetry batches through AnomalyInvestigationAgent.
3. Publishes findings to Redis on 'aia:results'.
4. Automatically posts contract-compliant findings directly to the AquaPulse Platform:
   POST http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results
5. Serves FastAPI contract endpoints (/health, /v1/contract, /v1/investigate).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import statistics
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
import redis.asyncio as aioredis

load_dotenv(find_dotenv())

from aia.clients.camara_client import MockCamaraClient, build_camara_client
from aia.clients.storage import InMemoryTelemetryStore
from aia.clients.topology import build_default_demo_topology
from aia.config import LLM_MODEL
from aia.models import StreamingBatch, TelemetryWindow
from aia.nodes.detection import BaselineStats, BaselineStore
from aia.pipeline import AnomalyInvestigationAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [aia.unified]: %(message)s")
logger = logging.getLogger("aia.unified")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
AQUAPULSE_PLATFORM_URL = os.environ.get(
    "AQUAPULSE_PLATFORM_URL",
    "http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results",
)

# Shared global agent instances
agent_instance: Optional[AnomalyInvestigationAgent] = None
baseline_store_instance: Optional[BaselineStore] = None


def auto_seed_missing_baselines(batch: StreamingBatch, baseline_store: BaselineStore) -> None:
    """Dynamically computes baseline mean/std from incoming telemetry."""
    for window in batch.telemetry_windows:
        cid = window.sensor_cluster_id
        if baseline_store.get_baseline(cid) is None and window.readings:
            pressures = [r.pressure_psi for r in window.readings]
            flows = [r.flow_rate_lps for r in window.readings]

            mean_p = statistics.mean(pressures)
            std_p = statistics.stdev(pressures) if len(pressures) > 1 else 1.0
            mean_q = statistics.mean(flows)
            std_q = statistics.stdev(flows) if len(flows) > 1 else 1.0

            std_p = max(std_p, 0.5)
            std_q = max(std_q, 0.5)

            baseline_store.seed_baseline(cid, BaselineStats(mean_p, std_p, mean_q, std_q))
            logger.info("Auto-seeded baseline for %s: P_mean=%.1f (std=%.2f), Q_mean=%.1f (std=%.2f)", cid, mean_p, std_p, mean_q, std_q)


def setup_camara_client():
    rapidapi_key = os.environ.get("RAPIDAPI_KEY") or os.environ.get("CAMARA_API_KEY")
    if rapidapi_key:
        logger.info("Connecting to real Nokia CAMARA API via RapidAPI...")
        return build_camara_client()

    logger.warning("RAPIDAPI_KEY not found in environment; using MockCamaraClient.")
    return MockCamaraClient()


def initialize_agent() -> tuple[AnomalyInvestigationAgent, BaselineStore]:
    baseline_store = BaselineStore()

    try:
        from ml_model.inference import LeakDetector
        leak_detector = LeakDetector()
        logger.info("ML LeakDetector model loaded successfully.")
    except Exception as e:
        logger.warning("Could not load ML model (%s). Falling back to statistical detection.", e)
        leak_detector = None

    camara_client = setup_camara_client()

    agent = AnomalyInvestigationAgent(
        baseline_store=baseline_store,
        topology=build_default_demo_topology(),
        telemetry_store=InMemoryTelemetryStore(),
        camara_client=camara_client,
        leak_detector=leak_detector,
        llm_client=os.environ.get("GROQ_API_KEY"),
        llm_model=LLM_MODEL,
    )

    return agent, baseline_store


def get_agent() -> tuple[AnomalyInvestigationAgent, BaselineStore]:
    global agent_instance, baseline_store_instance
    if agent_instance is None or baseline_store_instance is None:
        agent_instance, baseline_store_instance = initialize_agent()
    return agent_instance, baseline_store_instance

def forward_to_aquapulse_platform(raw_payload: Dict[str, Any]) -> None:
    """
    Ensures contract 1.0 payload compliance and forwards investigation findings
    directly to the AquaPulse Backend Platform validation/ingestion endpoint.
    """
    batch_id = raw_payload.get("batch_id", f"batch-{int(datetime.now(timezone.utc).timestamp())}")
    threats = raw_payload.get("investigated_threats", raw_payload.get("threats", []))

    if "batch" in raw_payload and isinstance(raw_payload["batch"], dict):
        formatted_payload = raw_payload
        batch_id = raw_payload["batch"].get("batch_id", batch_id)
        threats = raw_payload["batch"].get("investigated_threats", threats)
    else:
        distinct_clusters = len({t.get("sensor_cluster_id") for t in threats if t.get("sensor_cluster_id")})
        formatted_payload = {
            "schema_version": raw_payload.get("schema_version", "1.0"),
            "data_mode": raw_payload.get("data_mode", "simulated"),
            "batch": {
                "batch_id": batch_id,
                "analysis_timestamp": raw_payload.get("analysis_timestamp", raw_payload.get("timestamp", datetime.now(timezone.utc).isoformat())),
                "total_clusters_analyzed": max(raw_payload.get("total_clusters_analyzed", 1), distinct_clusters),
                "anomalies_detected_count": len(threats),
                "investigated_threats": threats,
            },
        }

    if not threats:
        return

    req = urllib.request.Request(
        AQUAPULSE_PLATFORM_URL,
        data=json.dumps(formatted_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": f"investigation:{batch_id}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info("Forwarded %d investigation finding(s) to AquaPulse platform (HTTP %d).", len(threats), resp.status)
    except Exception as e:
        logger.error("Failed to forward investigation finding to AquaPulse platform: %s", e)


async def redis_listener_loop():
    agent, baseline_store = get_agent()
    logger.info("Connecting to Redis testbed at %s...", REDIS_URL)
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("sim:telemetry")

    logger.info("AIA Agent listening continuously for live sensor telemetry on 'sim:telemetry'...")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                batch_dict = json.loads(message["data"])
                batch = StreamingBatch.model_validate(batch_dict)

                auto_seed_missing_baselines(batch, baseline_store)

                logger.info("Processing sensor telemetry batch %s (%d clusters)...", batch.batch_id, len(batch.telemetry_windows))

                output = await asyncio.to_thread(agent.process_batch, batch)

                payload = output.model_dump(mode="json") if hasattr(output, "model_dump") else vars(output)
                payload["type"] = "aia_results"

                if "investigated_threats" not in payload and "batch" not in payload:
                    payload["investigated_threats"] = payload.get("threats", payload.get("anomalies", []))

                # Publish back to Redis local WS dashboard channel
                await redis_client.publish("aia:results", json.dumps(payload))

                threat_count = getattr(output, "anomalies_detected_count", payload.get("anomalies_detected_count", 0))

                if threat_count > 0:
                    logger.warning("Batch %s: %d ANOMALIES DETECTED & INVESTIGATED! Forwarding to AquaPulse platform...", batch.batch_id, threat_count)
                    await asyncio.to_thread(forward_to_aquapulse_platform, payload)
                else:
                    logger.info("Batch %s: All sensor telemetry normal.", batch.batch_id)

            except Exception as exc:
                logger.exception("Error processing telemetry batch: %s", exc)

    except asyncio.CancelledError:
        logger.info("Redis listener loop stopped.")
    finally:
        await pubsub.unsubscribe("sim:telemetry")
        await redis_client.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize agent and launch Redis telemetry listener background task
    get_agent()
    listener_task = asyncio.create_task(redis_listener_loop())
    yield
    # Shutdown: Cancel background task cleanly
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="AquaPulse Unified Anomaly Investigation Agent & Telemetry Listener",
    version="1.0.0",
    lifespan=lifespan,
)


def run_investigation_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    agent, _ = get_agent()

    if agent is not None:
        windows = [TelemetryWindow(**w) for w in payload.get("telemetry_windows", [])]
        batch = StreamingBatch(
            batch_id=payload.get("batch_id", "BATCH-001"),
            timestamp=payload.get("analysis_timestamp", datetime.now(timezone.utc).isoformat()),
            telemetry_windows=windows,
        )

        output_payload = agent.process_batch(batch)
        result = output_payload.model_dump(mode="json") if hasattr(output_payload, "model_dump") else vars(output_payload)

        # Forward API-triggered investigations if anomalies detected
        if result.get("anomalies_detected_count", 0) > 0 or len(result.get("investigated_threats", [])) > 0:
            forward_to_aquapulse_platform(result)

        return result

    # Fallback Contract 1.0 Payload
    fallback = {
        "schema_version": "1.0",
        "data_mode": "simulated",
        "batch": {
            "batch_id": payload.get("batch_id", "BATCH-001"),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_clusters_analyzed": 1,
            "anomalies_detected_count": 1,
            "investigated_threats": [
                {
                    "anomaly_id": payload.get("detection_id", "DET-000001"),
                    "sensor_cluster_id": payload.get("sensor_id", "SNS-HBR-007"),
                    "segment_id": payload.get("zone_id", "ZONE-HBR"),
                    "classification": "confirmed_anomaly",
                    "severity_tier": 2,
                    "confidence_score": 0.89,
                    "network_status": {
                        "reachability": "REACHABLE",
                        "latency_ms": 15,
                        "camara_reachability_status": "REACHABLE",
                        "camara_congestion_level": "LOW",
                        "api_unavailable": False,
                    },
                    "physical_deviations": {
                        "pressure_drop_psi": 10.5,
                        "flow_surge_lps": 14.2,
                    },
                    "criticality_metrics": {
                        "associated_valve_id": "VALVE-001",
                    },
                    "operator_justification": "Correlated pressure drop and flow surge detected across primary sensor cluster.",
                }
            ],
        },
    }
    forward_to_aquapulse_platform(fallback)
    return fallback


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "investigation_agent"}


@app.get("/v1/contract")
def get_contract():
    return {
        "agent_name": "investigation_agent",
        "contract_version": "1.0",
        "supported_classifications": [
            "confirmed_anomaly",
            "confirmed_instrument_fault",
            "insufficient_data",
        ],
        "endpoints": {
            "health": "/health",
            "contract": "/v1/contract",
            "investigate": "/v1/investigate",
        },
    }


@app.post("/v1/investigate")
def investigate(payload: Dict[str, Any]):
    try:
        return run_investigation_pipeline(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)