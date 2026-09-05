from __future__ import annotations

from aia.models import Classification, ClusterInvestigationState, CongestionLevel, ReachabilityStatus
from tests.conftest import make_window
from aia.nodes.risk import assess_risk


def _confirmed_state(cluster_id: str, values) -> ClusterInvestigationState:
    window = make_window(cluster_id, values)
    state = ClusterInvestigationState(sensor_cluster_id=cluster_id, window=window)
    state.classification = Classification.CONFIRMED_ANOMALY
    state.camara_reachability_status = ReachabilityStatus.REACHABLE
    state.camara_congestion_level = CongestionLevel.LOW
    state.api_unavailable = False
    return state


def test_tier3_catastrophic_rupture(topology):
    # cluster-a has criticality 3; 10 readings, sharp drop + steep negative slope
    values = [(45.0, 80.0, 40.0)] * 3 + [(20.0, 130.0, 40.0)] * 7
    state = _confirmed_state("cluster-a", values)
    assess_risk(state, topology)
    assert state.criticality_score == 3
    assert state.pressure_drop_pct >= 35.0
    assert state.severity_tier == 3


def test_tier1_minor_low_criticality(topology):
    values = [(45.0, 80.0, 40.0)] * 5 + [(44.0, 81.0, 40.0)] * 5  # <15% drop
    state = _confirmed_state("cluster-b", values)  # criticality 1
    assess_risk(state, topology)
    assert state.severity_tier == 1


def test_tier2_moderate_criticality_two():
    from aia.clients.topology import (
        ClusterTopologyMapping,
        InMemoryTopologyCache,
        SegmentTopology,
    )

    topo = InMemoryTopologyCache()
    topo.load([
        ClusterTopologyMapping(
            sensor_cluster_id="cluster-c",
            segment=SegmentTopology(
                segment_id="seg-c", criticality_score=2, proximity_to_reservoir_m=1000.0,
                population_served=5000, associated_valve_id="valve-c",
            ),
        )
    ])
    values = [(45.0, 80.0, 40.0)] * 5 + [(44.5, 80.5, 40.0)] * 5  # tiny drop, but criticality==2 forces Tier 2
    state = _confirmed_state("cluster-c", values)
    assess_risk(state, topo)
    assert state.severity_tier == 2


def test_instrument_fault_bypasses_risk_matrix_and_marks_stale(topology):
    values = [(45.0, 80.0, 40.0)] * 5 + [(0.0, 0.0, 40.0)] * 5
    window = make_window("cluster-b", values)
    state = ClusterInvestigationState(sensor_cluster_id="cluster-b", window=window)
    state.classification = Classification.CONFIRMED_INSTRUMENT_FAULT
    state.camara_reachability_status = ReachabilityStatus.UNREACHABLE
    state.camara_congestion_level = CongestionLevel.LOW
    assess_risk(state, topology)
    assert state.severity_tier == 1
    assert state.is_stale_pre_outage_data is True


def test_confidence_score_penalized_when_api_unavailable(topology):
    state = _confirmed_state("cluster-a", [(45.0, 80.0, 40.0)] * 10)
    state.api_unavailable = True
    assess_risk(state, topology)
    # C_CAMARA term drops to 0 -> score should be noticeably below a fully-confident case
    assert state.confidence_score < 0.65
