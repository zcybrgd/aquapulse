"""
Integration tests reproducing the five target simulation scenarios from
Section 9, Phase 3 of the spec, run through the full AnomalyInvestigationAgent
pipeline (Stage 1 -> Stage 4).
"""
from __future__ import annotations

from datetime import datetime, timezone

from aia.camara_client import MockCamaraClient
from aia.models import Classification, CongestionLevel, ReachabilityStatus, StreamingBatch
from aia.pipeline import AnomalyInvestigationAgent
from tests.conftest import make_window


def _agent(camara_client, baseline_store, topology, telemetry_store) -> AnomalyInvestigationAgent:
    return AnomalyInvestigationAgent(
        baseline_store=baseline_store,
        topology=topology,
        telemetry_store=telemetry_store,
        camara_client=camara_client,
    )


def _batch(window) -> StreamingBatch:
    return StreamingBatch(
        batch_id="test-batch",
        timestamp=datetime(2026, 8, 31, 2, 0, tzinfo=timezone.utc),
        telemetry_windows=[window],
    )


def test_scenario_a_thermal_cellular_outage(baseline_store, topology, telemetry_store):
    """52C heat, high packet loss, UNREACHABLE + HIGH congestion -> likely_connectivity_artifact."""
    window = make_window("cluster-a", [(45.0, 80.0, 52.0)] * 5 + [(20.0, 130.0, 52.0)] * 5)
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.UNREACHABLE, "congestion": CongestionLevel.HIGH}
    })
    payload = _agent(client, baseline_store, topology, telemetry_store).process_batch(_batch(window))

    assert payload.anomalies_detected_count == 1
    threat = payload.investigated_threats[0]
    assert threat.classification == Classification.LIKELY_CONNECTIVITY_ARTIFACT
    assert threat.severity_tier == 1
    assert threat.confidence_score >= 0.60  # telemetry+trend complete, only CAMARA partially degraded is not the case here (both calls succeeded)


def test_scenario_b_catastrophic_leak(baseline_store, topology, telemetry_store):
    """48C, REACHABLE + LOW congestion, 40%+ pressure drop near reservoir -> confirmed_anomaly Tier 3."""
    window = make_window("cluster-a", [(45.0, 80.0, 48.0)] * 3 + [(20.0, 140.0, 48.0)] * 7)
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.REACHABLE, "congestion": CongestionLevel.LOW}
    })
    payload = _agent(client, baseline_store, topology, telemetry_store).process_batch(_batch(window))

    threat = payload.investigated_threats[0]
    assert threat.classification == Classification.CONFIRMED_ANOMALY
    assert threat.severity_tier == 3
    assert threat.confidence_score >= 0.90


def test_scenario_c_instrument_fault(baseline_store, topology, telemetry_store):
    """45C, UNREACHABLE + LOW congestion, instantaneous flatline -> confirmed_instrument_fault, stale data."""
    window = make_window("cluster-a", [(45.0, 80.0, 45.0)] * 5 + [(0.0, 0.0, 45.0)] * 5)
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.UNREACHABLE, "congestion": CongestionLevel.LOW}
    })
    payload = _agent(client, baseline_store, topology, telemetry_store).process_batch(_batch(window))

    threat = payload.investigated_threats[0]
    assert threat.classification == Classification.CONFIRMED_INSTRUMENT_FAULT
    assert threat.physical_deviations.is_stale_pre_outage_data is True
    assert threat.confidence_score >= 0.60


def test_scenario_d_api_downtime_fallback(baseline_store, topology, telemetry_store):
    """Simulated socket error on CAMARA calls -> insufficient_data, api_unavailable, fallback tier."""
    window = make_window("cluster-a", [(45.0, 80.0, 40.0)] * 5 + [(20.0, 130.0, 40.0)] * 5)
    client = MockCamaraClient(overrides={"cluster-a": {"raise": True}})
    payload = _agent(client, baseline_store, topology, telemetry_store).process_batch(_batch(window))

    threat = payload.investigated_threats[0]
    assert threat.classification == Classification.INSUFFICIENT_DATA
    assert threat.network_status.api_unavailable is True
    assert threat.severity_tier == 2  # API_UNAVAILABLE_FALLBACK_TIER


def test_scenario_e_flapping_reachability_escalates_on_third_cycle(baseline_store, topology, telemetry_store):
    """Batches 1 & 2 re-queued; batch 3 triggers immediate human operator escalation."""
    client = MockCamaraClient(overrides={"cluster-a": {"raise": True}})
    agent = _agent(client, baseline_store, topology, telemetry_store)

    window = make_window("cluster-a", [(45.0, 80.0, 40.0)] * 5 + [(20.0, 130.0, 40.0)] * 5)

    escalations = []
    for cycle in range(3):
        payload = agent.process_batch(_batch(window))
        threat = payload.investigated_threats[0]
        assert threat.classification == Classification.INSUFFICIENT_DATA
        state_cycles = agent.retry_tracker.get("cluster-a")
        escalations.append(state_cycles)

    # After 3 consecutive cycles, the retry tracker should show escalation-eligible count
    assert agent.retry_tracker.get("cluster-a") == 3
