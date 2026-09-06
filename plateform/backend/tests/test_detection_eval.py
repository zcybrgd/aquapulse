from datetime import datetime, timedelta, timezone

from app.detection.rules import (
    ReadingPoint,
    evaluate_combined_leak_pattern,
    evaluate_connectivity,
    evaluate_flow_surge,
    evaluate_missing_telemetry,
    evaluate_pressure_drop,
    evaluate_sensor_quality,
)
from app.detection.scoring import priority_for_score, score_components
from app.services.telemetry_patterns import scenario_reading_values


def _series(start: datetime, values: list[float], attr: str) -> list[ReadingPoint]:
    points: list[ReadingPoint] = []
    for index, value in enumerate(values):
        kwargs = {attr: value}
        points.append(ReadingPoint(time=start + timedelta(minutes=index * 5), **kwargs))
    return points


def test_pressure_drop_at_threshold() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = _series(start, [400.0, 390.0, 380.0, 368.0], "pressure_kpa")
    hit = evaluate_pressure_drop(
        readings,
        threshold_pct=8.0,
        minimum_points=4,
        window_start=start,
        window_end=readings[-1].time,
    )
    assert hit.triggered is True
    assert "pressure_drop" in hit.reason_codes
    assert any(item.evidence_type == "percent_change" for item in hit.evidence)


def test_pressure_drop_below_threshold() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = _series(start, [400.0, 398.0, 396.0, 394.0], "pressure_kpa")
    hit = evaluate_pressure_drop(
        readings,
        threshold_pct=8.0,
        minimum_points=4,
        window_start=start,
        window_end=readings[-1].time,
    )
    assert hit.triggered is False


def test_flow_surge_at_threshold() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = _series(start, [50.0, 52.0, 54.0, 56.0], "flow_lps")
    hit = evaluate_flow_surge(
        readings,
        threshold_pct=12.0,
        minimum_points=4,
        window_start=start,
        window_end=readings[-1].time,
    )
    assert hit.triggered is True


def test_flow_surge_below_threshold() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = _series(start, [50.0, 51.0, 51.5, 52.0], "flow_lps")
    hit = evaluate_flow_surge(
        readings,
        threshold_pct=12.0,
        minimum_points=4,
        window_start=start,
        window_end=readings[-1].time,
    )
    assert hit.triggered is False


def test_combined_requires_both() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = [
        ReadingPoint(time=start + timedelta(minutes=i * 5), pressure_kpa=400 - i * 20, flow_lps=50 + i * 4)
        for i in range(4)
    ]
    hit = evaluate_combined_leak_pattern(
        readings,
        pressure_drop_pct=8.0,
        flow_surge_pct=12.0,
        minimum_points=4,
        window_start=start,
        window_end=readings[-1].time,
    )
    assert hit.triggered is True
    assert hit.reason_codes == ["combined_pressure_drop_and_flow_surge"]
    assert hit.metric_count == 2

    pressure_only = [
        ReadingPoint(time=start + timedelta(minutes=i * 5), pressure_kpa=400 - i * 20, flow_lps=50.0)
        for i in range(4)
    ]
    missed = evaluate_combined_leak_pattern(
        pressure_only,
        pressure_drop_pct=8.0,
        flow_surge_pct=12.0,
        minimum_points=4,
        window_start=start,
        window_end=pressure_only[-1].time,
    )
    assert missed.triggered is False


def test_connectivity_packet_loss() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = [
        ReadingPoint(time=start + timedelta(minutes=i * 5), packet_loss_pct=12.0, signal_strength_dbm=-70)
        for i in range(4)
    ]
    hit = evaluate_connectivity(
        readings,
        packet_loss_threshold=10.0,
        signal_threshold_dbm=-100.0,
        intermittent_gap_minutes=15.0,
        minimum_points=3,
        window_start=start,
        window_end=readings[-1].time,
    )
    assert hit.triggered is True
    assert "packet_loss_high" in hit.reason_codes


def test_frozen_sensor() -> None:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    readings = [
        ReadingPoint(time=start + timedelta(minutes=i * 5), pressure_kpa=412.0, flow_lps=54.0)
        for i in range(6)
    ]
    hit = evaluate_sensor_quality(
        readings,
        metadata={"measurement_types": ["pressure", "flow"], "measurement_ranges": []},
        fallback_ranges={"pressure_kpa": {"min": 50, "max": 1600}, "flow_lps": {"min": 0, "max": 120}},
        frozen_minutes=15,
        frozen_minimum_points=5,
        inconsistent_ratio_max=50,
        minimum_points=4,
        window_start=start,
        window_end=readings[-1].time,
        use_sensor_ranges=True,
    )
    assert hit.triggered is True
    assert "frozen_value" in hit.reason_codes


def test_missing_telemetry_boundary() -> None:
    latest = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    now = latest + timedelta(minutes=30)
    just_inside = evaluate_missing_telemetry(
        latest=latest,
        has_prior_readings=True,
        freshness_minutes=30,
        now=now - timedelta(seconds=1),
        require_prior=True,
    )
    at_threshold = evaluate_missing_telemetry(
        latest=latest,
        has_prior_readings=True,
        freshness_minutes=30,
        now=now,
        require_prior=True,
    )
    assert just_inside.triggered is False
    assert at_threshold.triggered is True


def test_score_range_and_priority() -> None:
    explanation = score_components(
        severity_weight=0.9,
        observed_ratio=16.0,
        threshold=8.0,
        metric_count=2,
        criticality_score=3,
        packet_loss_pct=4.0,
        health_score=70.0,
    )
    assert 0 <= explanation["anomaly_score"] <= 1
    assert abs(sum(explanation["weights"].values()) - 1.0) < 1e-9
    assert priority_for_score(0.0) == "low"
    assert priority_for_score(0.35) == "medium"
    assert priority_for_score(0.55) == "high"
    assert priority_for_score(0.80) == "critical"
    assert priority_for_score(1.0) == "critical"


def test_scenario_patterns_are_reproducible() -> None:
    when = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    first = scenario_reading_values("SNS-HBR-007", when, "online", scenario="combined_leak_pattern", step=9, total_steps=10)
    second = scenario_reading_values("SNS-HBR-007", when, "online", scenario="combined_leak_pattern", step=9, total_steps=10)
    assert first == second
    assert scenario_reading_values("SNS-HBR-007", when, "online", scenario="missing_telemetry", step=0, total_steps=1) is None
    frozen_a = scenario_reading_values("SNS-HBR-007", when, "online", scenario="frozen_sensor", step=0, total_steps=5)
    frozen_b = scenario_reading_values(
        "SNS-HBR-007",
        when + timedelta(days=3, hours=3, minutes=9),
        "online",
        scenario="frozen_sensor",
        step=4,
        total_steps=5,
    )
    assert frozen_a == frozen_b
