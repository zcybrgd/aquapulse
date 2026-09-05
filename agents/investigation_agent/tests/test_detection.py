from __future__ import annotations

from tests.conftest import make_window

from aia.nodes.detection import detect

def test_healthy_window_not_suspicious(baseline_store):
    window = make_window("cluster-a", [(45.0, 80.0, 40.0)] * 5)
    result = detect(window, baseline_store)
    assert result.is_suspicious is False


def test_sharp_pressure_drop_flags_suspicious(baseline_store):
    # 15%+ pressure drop within the window -> deterministic floor trips regardless of Z-score
    window = make_window("cluster-a", [(45.0, 80.0, 40.0), (45.0, 80.0, 40.0), (37.0, 80.0, 40.0)])
    result = detect(window, baseline_store)
    assert result.is_suspicious is True
    assert "pressure drop" in result.reason


def test_sharp_flow_surge_flags_suspicious(baseline_store):
    window = make_window("cluster-a", [(45.0, 80.0, 40.0), (45.0, 80.0, 40.0), (45.0, 100.0, 40.0)])
    result = detect(window, baseline_store)
    assert result.is_suspicious is True
    assert "flow surge" in result.reason


def test_z_score_breach_flags_suspicious(baseline_store):
    # baseline mean=45 std=0.5 -> a reading of 50 is 10 std devs away
    window = make_window("cluster-a", [(45.0, 80.0, 40.0), (45.0, 80.0, 40.0), (50.0, 80.0, 40.0)])
    result = detect(window, baseline_store)
    assert result.is_suspicious is True
    assert abs(result.z_score_pressure) >= 3.0


def test_safety_floor_not_relaxed_by_temperature(baseline_store):
    """Safety Separation Rule: the deterministic floor must trip even at extreme heat."""
    window = make_window("cluster-a", [(45.0, 80.0, 55.0), (45.0, 80.0, 55.0), (37.0, 80.0, 55.0)])
    result = detect(window, baseline_store)
    assert result.is_suspicious is True
