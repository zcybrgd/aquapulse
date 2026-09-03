"""
Example run of the Anomaly Investigation Agent, reproducing the three
clusters described in the spec (Section 3 input example + Section 7 output
example):

  - cluster-desert-042: catastrophic leak near a NEOM reservoir -> Tier 3
  - cluster-desert-043: healthy telemetry -> archived, never investigated
  - cluster-desert-044: sensor gone dark, low congestion -> instrument fault

Run with:  python -m aia.main
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from aia.camara_client import MockCamaraClient
from aia.detection import BaselineStats, BaselineStore
from aia.models import CongestionLevel, NetworkMetadata, ReachabilityStatus, Reading, StreamingBatch, TelemetryWindow
from aia.pipeline import AnomalyInvestigationAgent
from aia.storage import InMemoryTelemetryStore
from aia.topology import build_default_demo_topology

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


def build_demo_camara_client() -> MockCamaraClient:
    return MockCamaraClient(overrides={
        "cluster-desert-042": {
            "reachability": ReachabilityStatus.REACHABLE,
            "congestion": CongestionLevel.LOW,
        },
        "cluster-desert-044": {
            "reachability": ReachabilityStatus.UNREACHABLE,
            "congestion": CongestionLevel.LOW,
        },
    })


def main() -> None:
    agent = AnomalyInvestigationAgent(
        baseline_store=build_seeded_baselines(),
        topology=build_default_demo_topology(),
        telemetry_store=InMemoryTelemetryStore(),
        camara_client=build_demo_camara_client(),
        anthropic_client=None,  # falls back to the deterministic narrator; pass an
                                 # anthropic.Anthropic() instance to use live narration
    )

    batch = build_demo_batch()
    payload = agent.process_batch(batch)

    print(json.dumps(payload.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
