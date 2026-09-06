"""Pure deterministic rule evaluation. Same inputs produce the same outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.services.telemetry_constants import KPA_TO_BAR, LPS_TO_M3H


@dataclass(frozen=True)
class ReadingPoint:
    time: datetime
    pressure_kpa: float | None = None
    flow_lps: float | None = None
    temperature_c: float | None = None
    signal_strength_dbm: int | None = None
    packet_loss_pct: float | None = None
    battery_pct: float | None = None


@dataclass
class EvidenceItem:
    metric: str
    observed_value: float
    unit: str
    evidence_type: str
    baseline_value: float | None = None
    threshold_value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleHit:
    triggered: bool
    reason_codes: list[str]
    trigger_reason: str
    evidence: list[EvidenceItem]
    observed_ratio: float
    metric_count: int
    window_start: datetime
    window_end: datetime
    reading_count: int


def _series(readings: list[ReadingPoint], attr: str) -> list[tuple[datetime, float]]:
    points: list[tuple[datetime, float]] = []
    for reading in readings:
        value = getattr(reading, attr)
        if value is not None:
            points.append((reading.time, float(value)))
    return points


def _percent_change(first: float, last: float) -> float:
    if first == 0:
        return 0.0 if last == 0 else 100.0
    return ((last - first) / abs(first)) * 100.0


def _window_bounds(readings: list[ReadingPoint]) -> tuple[datetime, datetime]:
    times = [item.time for item in readings]
    return min(times), max(times)


def evaluate_pressure_drop(
    readings: list[ReadingPoint],
    *,
    threshold_pct: float,
    minimum_points: int,
    window_start: datetime,
    window_end: datetime,
) -> RuleHit:
    series = _series(readings, "pressure_kpa")
    empty = RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=window_start,
        window_end=window_end,
        reading_count=len(readings),
    )
    if len(series) < minimum_points:
        return empty
    first_time, first = series[0]
    last_time, last = series[-1]
    change_pct = _percent_change(first, last)
    drop_pct = -change_pct
    triggered = drop_pct >= threshold_pct
    if not triggered:
        return empty
    evidence = [
        EvidenceItem("pressure_kpa", first, "kPa", "first_value", details={"time": first_time.isoformat()}),
        EvidenceItem("pressure_kpa", last, "kPa", "last_value", details={"time": last_time.isoformat()}),
        EvidenceItem(
            "pressure_kpa",
            round(last - first, 4),
            "kPa",
            "absolute_change",
            baseline_value=first,
            threshold_value=threshold_pct,
        ),
        EvidenceItem(
            "pressure_kpa",
            round(change_pct, 4),
            "%",
            "percent_change",
            baseline_value=first,
            threshold_value=threshold_pct,
            details={"window_minutes": (last_time - first_time).total_seconds() / 60.0},
        ),
    ]
    return RuleHit(
        triggered=True,
        reason_codes=["pressure_drop"],
        trigger_reason=(
            f"Pressure fell {drop_pct:.1f}% (threshold {threshold_pct:.1f}%) "
            f"from {first:.1f} kPa to {last:.1f} kPa."
        ),
        evidence=evidence,
        observed_ratio=drop_pct,
        metric_count=1,
        window_start=first_time,
        window_end=last_time,
        reading_count=len(readings),
    )


def evaluate_flow_surge(
    readings: list[ReadingPoint],
    *,
    threshold_pct: float,
    minimum_points: int,
    window_start: datetime,
    window_end: datetime,
) -> RuleHit:
    series = _series(readings, "flow_lps")
    empty = RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=window_start,
        window_end=window_end,
        reading_count=len(readings),
    )
    if len(series) < minimum_points:
        return empty
    first_time, first = series[0]
    last_time, last = series[-1]
    change_pct = _percent_change(first, last)
    triggered = change_pct >= threshold_pct
    if not triggered:
        return empty
    evidence = [
        EvidenceItem("flow_lps", first, "L/s", "first_value", details={"time": first_time.isoformat()}),
        EvidenceItem("flow_lps", last, "L/s", "last_value", details={"time": last_time.isoformat()}),
        EvidenceItem(
            "flow_lps",
            round(last - first, 4),
            "L/s",
            "absolute_change",
            baseline_value=first,
            threshold_value=threshold_pct,
        ),
        EvidenceItem(
            "flow_lps",
            round(change_pct, 4),
            "%",
            "percent_change",
            baseline_value=first,
            threshold_value=threshold_pct,
        ),
    ]
    return RuleHit(
        triggered=True,
        reason_codes=["flow_surge"],
        trigger_reason=(
            f"Flow rose {change_pct:.1f}% (threshold {threshold_pct:.1f}%) "
            f"from {first:.3f} L/s to {last:.3f} L/s."
        ),
        evidence=evidence,
        observed_ratio=change_pct,
        metric_count=1,
        window_start=first_time,
        window_end=last_time,
        reading_count=len(readings),
    )


def evaluate_combined_leak_pattern(
    readings: list[ReadingPoint],
    *,
    pressure_drop_pct: float,
    flow_surge_pct: float,
    minimum_points: int,
    window_start: datetime,
    window_end: datetime,
) -> RuleHit:
    pressure = evaluate_pressure_drop(
        readings,
        threshold_pct=pressure_drop_pct,
        minimum_points=minimum_points,
        window_start=window_start,
        window_end=window_end,
    )
    flow = evaluate_flow_surge(
        readings,
        threshold_pct=flow_surge_pct,
        minimum_points=minimum_points,
        window_start=window_start,
        window_end=window_end,
    )
    empty = RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=window_start,
        window_end=window_end,
        reading_count=len(readings),
    )
    if not (pressure.triggered and flow.triggered):
        return empty
    observed = max(pressure.observed_ratio, flow.observed_ratio)
    return RuleHit(
        triggered=True,
        reason_codes=["combined_pressure_drop_and_flow_surge"],
        trigger_reason=(
            "Pressure decreased and flow increased in the same window "
            f"(pressure {pressure.observed_ratio:.1f}%, flow {flow.observed_ratio:.1f}%). "
            "This is not a confirmed leak."
        ),
        evidence=pressure.evidence + flow.evidence,
        observed_ratio=observed,
        metric_count=2,
        window_start=min(pressure.window_start, flow.window_start),
        window_end=max(pressure.window_end, flow.window_end),
        reading_count=len(readings),
    )


def evaluate_connectivity(
    readings: list[ReadingPoint],
    *,
    packet_loss_threshold: float,
    signal_threshold_dbm: float,
    intermittent_gap_minutes: float,
    minimum_points: int,
    window_start: datetime,
    window_end: datetime,
) -> RuleHit:
    empty = RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=window_start,
        window_end=window_end,
        reading_count=len(readings),
    )
    if len(readings) < minimum_points:
        return empty
    packet_series = _series(readings, "packet_loss_pct")
    signal_series = _series(readings, "signal_strength_dbm")
    reasons: list[str] = []
    evidence: list[EvidenceItem] = []
    observed = 0.0
    summaries: list[str] = []

    if packet_series:
        mean_loss = sum(value for _, value in packet_series) / len(packet_series)
        max_loss = max(value for _, value in packet_series)
        if max_loss >= packet_loss_threshold:
            reasons.append("packet_loss_high")
            observed = max(observed, max_loss)
            summaries.append(
                f"packet loss reached {max_loss:.1f}% (threshold {packet_loss_threshold:.1f}%)"
            )
            evidence.append(
                EvidenceItem(
                    "packet_loss_pct",
                    max_loss,
                    "%",
                    "threshold_exceeded",
                    baseline_value=mean_loss,
                    threshold_value=packet_loss_threshold,
                )
            )

    if signal_series:
        min_signal = min(value for _, value in signal_series)
        if min_signal <= signal_threshold_dbm:
            reasons.append("signal_strength_low")
            observed = max(observed, abs(min_signal))
            summaries.append(
                f"signal fell to {min_signal:.0f} dBm (threshold {signal_threshold_dbm:.0f} dBm)"
            )
            evidence.append(
                EvidenceItem(
                    "signal_strength_dbm",
                    min_signal,
                    "dBm",
                    "threshold_exceeded",
                    threshold_value=signal_threshold_dbm,
                )
            )

    expected_gap = timedelta(minutes=intermittent_gap_minutes)
    times = [item.time for item in readings]
    max_gap = timedelta(0)
    for previous, current in zip(times, times[1:]):
        gap = current - previous
        if gap > max_gap:
            max_gap = gap
    if max_gap >= expected_gap and len(times) >= 2:
        reasons.append("intermittent_measurements")
        gap_minutes = max_gap.total_seconds() / 60.0
        observed = max(observed, gap_minutes)
        summaries.append(
            f"measurement gap of {gap_minutes:.1f} min exceeded "
            f"{intermittent_gap_minutes:.1f} min"
        )
        evidence.append(
            EvidenceItem(
                "freshness",
                gap_minutes,
                "min",
                "intermittent_gap",
                threshold_value=expected_gap.total_seconds() / 60.0,
            )
        )

    if not reasons:
        return empty
    start, end = _window_bounds(readings)
    return RuleHit(
        triggered=True,
        reason_codes=reasons,
        trigger_reason="Connectivity degradation: " + "; ".join(summaries) + ".",
        evidence=evidence,
        observed_ratio=observed,
        metric_count=len(reasons),
        window_start=start,
        window_end=end,
        reading_count=len(readings),
    )


def evaluate_missing_telemetry(
    *,
    latest: datetime | None,
    has_prior_readings: bool,
    freshness_minutes: float,
    now: datetime,
    require_prior: bool,
) -> RuleHit:
    empty = RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=now,
        window_end=now,
        reading_count=0,
    )
    if require_prior and not has_prior_readings:
        return empty
    if latest is None:
        if not has_prior_readings:
            return empty
        age_minutes = freshness_minutes + 1
        start = now
    else:
        age_minutes = (now - latest).total_seconds() / 60.0
        start = latest
    if age_minutes < freshness_minutes:
        return empty
    return RuleHit(
        triggered=True,
        reason_codes=["missing_telemetry"],
        trigger_reason=(
            f"No new reading for {age_minutes:.1f} min "
            f"(threshold {freshness_minutes:.1f} min)."
        ),
        evidence=[
            EvidenceItem(
                "freshness",
                round(age_minutes, 4),
                "min",
                "missing_reading",
                threshold_value=freshness_minutes,
                details={"latest_reading_at": latest.isoformat() if latest else None},
            )
        ],
        observed_ratio=age_minutes,
        metric_count=1,
        window_start=start,
        window_end=now,
        reading_count=0,
    )


def _metadata_ranges(metadata: dict[str, Any] | None) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    if not metadata:
        return ranges
    for item in metadata.get("measurement_ranges") or []:
        quantity = str(item.get("quantity", "")).lower()
        unit = str(item.get("unit", "")).lower()
        minimum = item.get("minimum")
        maximum = item.get("maximum")
        if minimum is None or maximum is None:
            continue
        if quantity == "pressure":
            if unit == "bar":
                ranges["pressure_kpa"] = (float(minimum) / KPA_TO_BAR, float(maximum) / KPA_TO_BAR)
            else:
                ranges["pressure_kpa"] = (float(minimum), float(maximum))
        elif quantity == "flow":
            if unit in {"m3/h", "m³/h"}:
                ranges["flow_lps"] = (float(minimum) / LPS_TO_M3H, float(maximum) / LPS_TO_M3H)
            else:
                ranges["flow_lps"] = (float(minimum), float(maximum))
        elif quantity == "temperature":
            ranges["temperature_c"] = (float(minimum), float(maximum))
    return ranges


def _measurement_types(metadata: dict[str, Any] | None) -> set[str]:
    if not metadata:
        return {"pressure", "flow", "temperature"}
    types = metadata.get("measurement_types")
    if not types:
        return {"pressure", "flow", "temperature"}
    mapping = {"pressure": "pressure_kpa", "flow": "flow_lps", "temperature": "temperature_c"}
    return {mapping.get(str(item).lower(), str(item).lower()) for item in types}


def evaluate_sensor_quality(
    readings: list[ReadingPoint],
    *,
    metadata: dict[str, Any] | None,
    fallback_ranges: dict[str, dict[str, float]],
    frozen_minutes: float,
    frozen_minimum_points: int,
    inconsistent_ratio_max: float,
    minimum_points: int,
    window_start: datetime,
    window_end: datetime,
    use_sensor_ranges: bool,
) -> RuleHit:
    empty = RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=window_start,
        window_end=window_end,
        reading_count=len(readings),
    )
    if len(readings) < minimum_points:
        return empty

    types = _measurement_types(metadata)
    sensor_ranges = _metadata_ranges(metadata) if use_sensor_ranges else {}
    ranges: dict[str, tuple[float, float]] = {}
    for metric, bounds in fallback_ranges.items():
        ranges[metric] = (float(bounds["min"]), float(bounds["max"]))
    ranges.update(sensor_ranges)

    reasons: list[str] = []
    evidence: list[EvidenceItem] = []
    summaries: list[str] = []
    observed = 0.0
    metric_map = {
        "pressure_kpa": ("pressure_kpa", "kPa"),
        "flow_lps": ("flow_lps", "L/s"),
        "temperature_c": ("temperature_c", "°C"),
    }

    for metric, (attr, unit) in metric_map.items():
        if metric not in types:
            continue
        series = _series(readings, attr)
        if not series:
            continue
        bounds = ranges.get(metric)
        if bounds is not None:
            for when, value in series:
                if value < bounds[0] or value > bounds[1]:
                    reasons.append("out_of_range")
                    observed = max(observed, abs(value))
                    summaries.append(f"{metric} {value} {unit} outside {bounds[0]}–{bounds[1]} {unit}")
                    evidence.append(
                        EvidenceItem(
                            metric,
                            value,
                            unit,
                            "out_of_range",
                            threshold_value=bounds[1] if value > bounds[1] else bounds[0],
                            details={"time": when.isoformat(), "min": bounds[0], "max": bounds[1]},
                        )
                    )
                    break

        if len(series) >= frozen_minimum_points:
            values = [value for _, value in series]
            if all(value == values[0] for value in values):
                span_minutes = (series[-1][0] - series[0][0]).total_seconds() / 60.0
                if span_minutes >= frozen_minutes or len(series) >= frozen_minimum_points:
                    reasons.append("frozen_value")
                    observed = max(observed, span_minutes)
                    summaries.append(
                        f"{metric} frozen at {values[0]} {unit} for {span_minutes:.1f} min"
                    )
                    evidence.append(
                        EvidenceItem(
                            metric,
                            values[0],
                            unit,
                            "frozen_value",
                            threshold_value=frozen_minutes,
                            details={"span_minutes": span_minutes, "points": len(series)},
                        )
                    )

    pressure = _series(readings, "pressure_kpa")
    flow = _series(readings, "flow_lps")
    if pressure and flow and "pressure_kpa" in types and "flow_lps" in types:
        last_p = pressure[-1][1]
        last_f = flow[-1][1]
        if last_f > 0:
            ratio = last_p / last_f
            if ratio > inconsistent_ratio_max:
                reasons.append("internally_inconsistent")
                observed = max(observed, ratio)
                summaries.append(
                    f"pressure/flow ratio {ratio:.1f} exceeded {inconsistent_ratio_max:.1f}"
                )
                evidence.append(
                    EvidenceItem(
                        "pressure_kpa",
                        ratio,
                        "kPa per L/s",
                        "inconsistent_ratio",
                        threshold_value=inconsistent_ratio_max,
                    )
                )

    if not reasons:
        return empty
    start, end = _window_bounds(readings)
    unique_reasons = list(dict.fromkeys(reasons))
    return RuleHit(
        triggered=True,
        reason_codes=unique_reasons,
        trigger_reason="Sensor quality anomaly: " + "; ".join(summaries) + ".",
        evidence=evidence,
        observed_ratio=observed,
        metric_count=len(unique_reasons),
        window_start=start,
        window_end=end,
        reading_count=len(readings),
    )
