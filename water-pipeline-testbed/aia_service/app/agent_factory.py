from __future__ import annotations

import config
from camara_sim_client import SimulatedCamaraClient
from topology import SEGMENTS

from aia.detection import BaselineStats, BaselineStore
from aia.pipeline import AnomalyInvestigationAgent, RetryTracker
from aia.storage import InMemoryTelemetryStore
from aia.topology import ClusterTopologyMapping, InMemoryTopologyCache, SegmentTopology


def _build_topology_cache() -> InMemoryTopologyCache:
    cache = InMemoryTopologyCache()
    cache.load([
        ClusterTopologyMapping(
            sensor_cluster_id=seg["sensor_cluster_id"],
            segment=SegmentTopology(
                segment_id=seg["segment_id"],
                criticality_score=seg["criticality_score"],
                proximity_to_reservoir_m=seg["proximity_to_reservoir_m"],
                population_served=seg["population_served"],
                associated_valve_id=seg["associated_valve_id"],
            ),
        )
        for seg in SEGMENTS
    ])
    return cache


def _build_baseline_store() -> BaselineStore:
    store = BaselineStore()
    for seg in SEGMENTS:
        # Modest std devs matching the simulator's normal-operation jitter
        # (physics.py's mean-reversion noise), so Stage 1's Z-score check is
        # tuned to the testbed's own baseline rather than production-scale data.
        store.seed_baseline(
            seg["sensor_cluster_id"],
            BaselineStats(
                pressure_mean=seg["baseline_pressure_psi"],
                pressure_std=max(0.8, seg["baseline_pressure_psi"] * 0.03),
                flow_mean=seg["baseline_flow_lps"],
                flow_std=max(1.2, seg["baseline_flow_lps"] * 0.06),
            ),
        )
    return store


def _build_anthropic_client():
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    except Exception:
        return None


def build_agent() -> AnomalyInvestigationAgent:
    return AnomalyInvestigationAgent(
        baseline_store=_build_baseline_store(),
        topology=_build_topology_cache(),
        telemetry_store=InMemoryTelemetryStore(),
        camara_client=SimulatedCamaraClient(config.SIMULATOR_URL),
        anthropic_client=_build_anthropic_client(),
        anthropic_model=config.ANTHROPIC_MODEL,
        retry_tracker=RetryTracker(),
    )
