from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from aia.clients.camara_client import MockCamaraClient, build_camara_client
from aia.clients.storage import InMemoryTelemetryStore
from aia.clients.topology import build_default_demo_topology
from aia.config import LLM_MODEL
from aia.models import (
    CongestionLevel,
    NetworkMetadata,
    ReachabilityStatus,
    Reading,
    StreamingBatch,
    TelemetryWindow,
)
from aia.nodes.detection import BaselineStats, BaselineStore
from aia.pipeline import AnomalyInvestigationAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _minute_readings(start: datetime, values: list[tuple[float, float, float]]) -> list[Reading]:
    return [
        Reading(
            timestamp=start + timedelta(minutes=i),
            pressure_psi=p,
            flow_rate_lps=q,
            ambient_temp_c=t,
        )
        for i, (p, q, t) in enumerate(values)
    ]


def build_demo_batch() -> StreamingBatch:
    t0 = datetime(2026, 8, 31, 1, 51, tzinfo=timezone.utc)

    cluster_042 = TelemetryWindow(
        sensor_cluster_id="cluster-desert-042",
        network_metadata=NetworkMetadata(signal_strength_dbm=-105, packet_loss_pct=12.5),
        readings=_minute_readings(t0, [
            (44.8, 80.2, 50.1), (44.5, 80.5, 50.3), (44.2, 80.1, 50.6),
            (44.0, 80.9, 50.9), (43.8, 81.1, 51.1), (43.1, 81.5, 51.3),
            (38.5, 95.2, 51.5), (32.4, 105.8, 51.6), (28.4, 112.5, 51.5),
        ]),
    )
    cluster_043 = TelemetryWindow(
        sensor_cluster_id="cluster-desert-043",
        network_metadata=NetworkMetadata(signal_strength_dbm=-72, packet_loss_pct=0.0),
        readings=_minute_readings(t0 + timedelta(minutes=4), [
            (45.1, 75.0, 51.0), (45.0, 75.1, 51.2), (45.1, 75.0, 51.3),
            (44.9, 75.2, 51.5), (45.0, 75.1, 51.4),
        ]),
    )
    cluster_044 = TelemetryWindow(
        sensor_cluster_id="cluster-desert-044",
        network_metadata=NetworkMetadata(signal_strength_dbm=None, packet_loss_pct=100.0),
        readings=_minute_readings(t0 + timedelta(minutes=4), [
            (45.2, 78.0, 45.0), (45.1, 78.2, 45.1), (45.0, 78.1, 45.3),
            (44.9, 78.0, 45.2), (0.0, 0.0, 45.4),
        ]),
    )

    return StreamingBatch(
        batch_id="batch-2026-08-31-001",
        timestamp=datetime(2026, 8, 31, 2, 0, 0, tzinfo=timezone.utc),
        telemetry_windows=[cluster_042, cluster_043, cluster_044],
    )


def build_seeded_baselines() -> BaselineStore:
    store = BaselineStore()
    store.seed_baseline("cluster-desert-042", BaselineStats(44.5, 0.6, 80.5, 0.8))
    store.seed_baseline("cluster-desert-043", BaselineStats(45.0, 0.3, 75.1, 0.3))
    store.seed_baseline("cluster-desert-044", BaselineStats(45.0, 0.3, 78.0, 0.3))
    return store


def setup_camara_client():
    """
    Connects to the real Nokia Network-as-Code / CAMARA API if RAPIDAPI_KEY is present.
    Falls back to MockCamaraClient when offline or during dry runs.
    """
    rapidapi_key = os.environ.get("RAPIDAPI_KEY") or os.environ.get("CAMARA_API_KEY")
    
    if rapidapi_key:
        logging.getLogger("aia").info("Connecting to real Nokia CAMARA API via RapidAPI...")
        return build_camara_client()
    
    logging.getLogger("aia").warning("RAPIDAPI_KEY not found in environment; using MockCamaraClient.")
    return MockCamaraClient(overrides={
        "cluster-desert-042": {
            "reachability": ReachabilityStatus.REACHABLE,
            "congestion": CongestionLevel.LOW,
        },
        "cluster-desert-043": {
            "reachability": ReachabilityStatus.REACHABLE,
            "congestion": CongestionLevel.LOW,
        },
        "cluster-desert-044": {
            "reachability": ReachabilityStatus.UNREACHABLE,
            "congestion": CongestionLevel.LOW,
        },
    })


def main() -> None:
    # Load ML Model
    try:
        from ml_model.inference import LeakDetector
        leak_detector = LeakDetector()
    except Exception as e:
        logging.getLogger("aia").warning(
            f"Could not load ML model ({e}). Falling back to statistical detection."
        )
        leak_detector = None

    camara_client = setup_camara_client()

    agent = AnomalyInvestigationAgent(
        baseline_store=build_seeded_baselines(),
        topology=build_default_demo_topology(),
        telemetry_store=InMemoryTelemetryStore(),
        camara_client=camara_client,
        leak_detector=leak_detector,
        llm_client=os.environ.get("GROQ_API_KEY"),
        llm_model=LLM_MODEL,
    )

    batch = build_demo_batch()
    payload = agent.process_batch(batch)

    print(json.dumps(payload.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()