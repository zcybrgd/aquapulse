from __future__ import annotations

from aia.camara_client import MockCamaraClient
from aia.investigation import investigate
from aia.models import Classification, ClusterInvestigationState, CongestionLevel, ReachabilityStatus
from tests.conftest import make_window


def _state(cluster_id: str, temp_c: float) -> ClusterInvestigationState:
    window = make_window(cluster_id, [(30.0, 100.0, temp_c)])
    return ClusterInvestigationState(sensor_cluster_id=cluster_id, window=window)


def test_reachable_device_is_confirmed_anomaly():
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.REACHABLE, "congestion": CongestionLevel.LOW}
    })
    state = investigate(_state("cluster-a", 40.0), client)
    assert state.classification == Classification.CONFIRMED_ANOMALY


def test_unreachable_high_congestion_hot_is_connectivity_artifact():
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.UNREACHABLE, "congestion": CongestionLevel.HIGH}
    })
    state = investigate(_state("cluster-a", 52.0), client)
    assert state.classification == Classification.LIKELY_CONNECTIVITY_ARTIFACT


def test_unreachable_low_congestion_is_instrument_fault():
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.UNREACHABLE, "congestion": CongestionLevel.LOW}
    })
    state = investigate(_state("cluster-a", 45.0), client)
    assert state.classification == Classification.CONFIRMED_INSTRUMENT_FAULT
    assert state.is_stale_pre_outage_data is True


def test_unreachable_high_congestion_but_cool_is_instrument_fault():
    """Thermal artifact requires BOTH high congestion AND temp >= 50C."""
    client = MockCamaraClient(overrides={
        "cluster-a": {"reachability": ReachabilityStatus.UNREACHABLE, "congestion": CongestionLevel.HIGH}
    })
    state = investigate(_state("cluster-a", 35.0), client)
    assert state.classification == Classification.CONFIRMED_INSTRUMENT_FAULT


def test_api_outage_never_infers_classification():
    client = MockCamaraClient(overrides={"cluster-a": {"raise": True}})
    state = investigate(_state("cluster-a", 40.0), client)
    assert state.classification == Classification.INSUFFICIENT_DATA
    assert state.api_unavailable is True
    assert state.requeue is True
