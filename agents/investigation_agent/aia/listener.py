"""
AIA Continuous Telemetry Listener.

Subscribes to the water simulator's `sim:telemetry` Redis Pub/Sub channel,
parses raw sensor readings, dynamically learns baselines, and triggers
full AIA investigations only when genuine anomalies occur.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import statistics
from dotenv import find_dotenv, load_dotenv
import redis.asyncio as aioredis

load_dotenv(find_dotenv())

from aia.clients.camara_client import MockCamaraClient, build_camara_client
from aia.clients.storage import InMemoryTelemetryStore
from aia.clients.topology import build_default_demo_topology
from aia.config import LLM_MODEL
from aia.models import (
    CongestionLevel,
    ReachabilityStatus,
    StreamingBatch,
    TelemetryWindow,
)
from aia.nodes.detection import BaselineStats, BaselineStore
from aia.pipeline import AnomalyInvestigationAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [aia.listener]: %(message)s")
logger = logging.getLogger("aia.listener")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def auto_seed_missing_baselines(batch: StreamingBatch, baseline_store: BaselineStore) -> None:
    """
    Dynamically computes baseline mean/std from the first incoming window
    for clusters not explicitly configured in BaselineStore.
    """
    for window in batch.telemetry_windows:
        cid = window.sensor_cluster_id
        if baseline_store.get_baseline(cid) is None and window.readings:
            pressures = [r.pressure_psi for r in window.readings]
            flows = [r.flow_rate_lps for r in window.readings]

            mean_p = statistics.mean(pressures)
            std_p = statistics.stdev(pressures) if len(pressures) > 1 else 1.0
            mean_q = statistics.mean(flows)
            std_q = statistics.stdev(flows) if len(flows) > 1 else 1.0

            # Prevent zero std deviation divisions
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


async def start_listening():
    logger.info("Initializing Anomaly Investigation Agent...")
    agent, baseline_store = initialize_agent()

    logger.info("Connecting to Redis testbed at %s...", REDIS_URL)
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("sim:telemetry")

    logger.info("AIA Agent listening continuously for live sensor telemetry on channel 'sim:telemetry'...")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                batch_dict = json.loads(message["data"])
                batch = StreamingBatch.model_validate(batch_dict)

                # Ensure baselines match actual simulator nominal values
                auto_seed_missing_baselines(batch, baseline_store)

                logger.info("Processing sensor telemetry batch %s (%d clusters)...", batch.batch_id, len(batch.telemetry_windows))

                # Process batch through AIA Agent
                output = await asyncio.to_thread(agent.process_batch, batch)

                # Convert output model to dictionary and format for Dashboard WS
                payload = output.model_dump(mode="json")
                payload["type"] = "aia_results"

                # Ensure field matches app.js feed expectation
                if "investigated_threats" not in payload:
                    payload["investigated_threats"] = payload.get("threats", payload.get("anomalies", []))

                # Broadcast analysis payload back to Redis on channel 'aia:results'
                await redis_client.publish("aia:results", json.dumps(payload))

                if output.anomalies_detected_count > 0:
                    logger.warning(
                        "Batch %s: %d ANOMALIES DETECTED & INVESTIGATED!",
                        batch.batch_id,
                        output.anomalies_detected_count,
                    )
                else:
                    logger.info("Batch %s: All sensor telemetry normal. No agent investigation required.", batch.batch_id)

            except Exception as exc:
                logger.exception("Error processing telemetry batch: %s", exc)

    except asyncio.CancelledError:
        logger.info("Listener stopped.")
    finally:
        await pubsub.unsubscribe("sim:telemetry")
        await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(start_listening())