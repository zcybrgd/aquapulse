from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aia.nodes.detection import BaselineStats, BaselineStore
from aia.models import NetworkMetadata, Reading, TelemetryWindow
from aia.clients.storage import InMemoryTelemetryStore
from aia.clients.topology import (
    ClusterTopologyMapping,
    InMemoryTopologyCache,
    SegmentTopology,
)

def make_window(
    cluster_id: str,
    values: list[tuple[float, float, float]],
    start=None,
) -> TelemetryWindow:
    start = start or datetime(
        2026,
        8,
        31,
        2,
        0,
        tzinfo=timezone.utc,
    )

    readings = [
        Reading(
            timestamp=start + timedelta(minutes=i),
            pressure_psi=p,
            flow_rate_lps=q,
            ambient_temp_c=t,
        )
        for i, (p, q, t) in enumerate(values)
    ]

    return TelemetryWindow(
        sensor_cluster_id=cluster_id,
        network_metadata=NetworkMetadata(),
        readings=readings,
    )


@pytest.fixture
def topology() -> InMemoryTopologyCache:
    cache = InMemoryTopologyCache()

    cache.load(
        [
            ClusterTopologyMapping(
                sensor_cluster_id="cluster-a",
                segment=SegmentTopology(
                    segment_id="seg-a",
                    criticality_score=3,
                    proximity_to_reservoir_m=100.0,
                    population_served=50000,
                    associated_valve_id="valve-a",
                ),
            ),
            ClusterTopologyMapping(
                sensor_cluster_id="cluster-b",
                segment=SegmentTopology(
                    segment_id="seg-b",
                    criticality_score=1,
                    proximity_to_reservoir_m=9000.0,
                    population_served=10,
                    associated_valve_id="valve-b",
                ),
            ),
        ]
    )

    return cache


@pytest.fixture
def baseline_store() -> BaselineStore:
    store = BaselineStore()

    store.seed_baseline(
        "cluster-a",
        BaselineStats(45.0, 0.5, 80.0, 0.5),
    )

    store.seed_baseline(
        "cluster-b",
        BaselineStats(45.0, 0.5, 80.0, 0.5),
    )

    return store


@pytest.fixture
def telemetry_store() -> InMemoryTelemetryStore:
    return InMemoryTelemetryStore()