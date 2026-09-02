"""
Stage 3: Deterministic Risk Assessment & Severity Tiering -- Section 5.C/5.D.

All math lives here in pure Python/NumPy -- the LLM never touches these
calculations (Section 6, "Strict LLM Boundary").
"""
from __future__ import annotations

import numpy as np

from aia.config import (
    CONFIDENCE_WEIGHT_CAMARA,
    CONFIDENCE_WEIGHT_TELEMETRY,
    CONFIDENCE_WEIGHT_TREND,
    EXPECTED_TELEMETRY_WINDOW_LEN,
    TIER1_CRITICALITY_MAX,
    TIER1_DELTA_P_PCT_MAX,
    TIER2_CRITICALITY_TRIGGER,
    TIER2_DELTA_P_PCT_MAX,
    TIER2_DELTA_P_PCT_MIN,
    TIER3_CRITICALITY_REQUIRED,
    TIER3_DELTA_P_PCT_MIN,
    TIER3_PRESSURE_SLOPE_MAX,
)
from aia.models import Classification, ClusterInvestigationState
from aia.topology import TopologyCache


def compute_trend(readings: list[float]) -> tuple[float, float]:
    """
    Linear-regression slope and R^2 of a value series over its reading index
    (Section 5.C.2). Returns (slope, r_squared). Slope units are per-reading;
    callers convert to psi/min using the sampling interval where needed.
    """
    n = len(readings)
    if n < 2:
        return 0.0, 1.0
    xs = np.arange(n, dtype=float)
    ys = np.array(readings, dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    predicted = slope * xs + intercept
    ss_res = float(np.sum((ys - predicted) ** 2))
    ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    return float(slope), max(0.0, min(1.0, r_squared))


def _slope_per_minute(readings, values: list[float]) -> float:
    """Convert an index-based slope into psi/min (or lps/min) using actual timestamps."""
    if len(readings) < 2:
        return 0.0
    total_minutes = (readings[-1].timestamp - readings[0].timestamp).total_seconds() / 60.0
    if total_minutes <= 0:
        return 0.0
    return (values[-1] - values[0]) / total_minutes


def compute_physical_deviations(state: ClusterInvestigationState) -> None:
    """Populate pressure/flow drop %, slopes, and trend fit onto `state` (Section 5.C.2)."""
    readings = state.window.readings
    pressures = [r.pressure_psi for r in readings]
    flows = [r.flow_rate_lps for r in readings]

    baseline_p, current_p = pressures[0], pressures[-1]
    baseline_q, current_q = flows[0], flows[-1]

    state.pressure_drop_pct = (
        (baseline_p - current_p) / baseline_p * 100.0 if baseline_p else 0.0
    )
    state.flow_surge_pct = (
        (current_q - baseline_q) / baseline_q * 100.0 if baseline_q else 0.0
    )
    state.pressure_slope = _slope_per_minute(readings, pressures)
    state.flow_slope = _slope_per_minute(readings, flows)
    _, state.trend_r_squared = compute_trend(pressures)


def assign_segment_metadata(state: ClusterInvestigationState, topology: TopologyCache) -> None:
    """Section 5.C.1: map the cluster to its physical segment via the local topology cache."""
    segment = topology.get_segment_for_cluster(state.sensor_cluster_id)
    if segment is None:
        # Unknown segment: treat conservatively as maximum criticality so a
        # topology-cache miss can never silently downgrade a real threat.
        state.segment_id = f"unknown-{state.sensor_cluster_id}"
        state.criticality_score = 3
        state.proximity_to_reservoir_m = 0.0
        state.population_served = 0
        state.associated_valve_id = f"unknown-{state.sensor_cluster_id}"
        return
    state.segment_id = segment.segment_id
    state.criticality_score = segment.criticality_score
    state.proximity_to_reservoir_m = segment.proximity_to_reservoir_m
    state.population_served = segment.population_served
    state.associated_valve_id = segment.associated_valve_id


def assign_severity_tier(state: ClusterInvestigationState) -> int:
    """
    Reconciled Risk Tiering Matrix (Section 5.C.3):
      Tier 3: delta_p% >= 35, pressure_slope < -2.0 psi/min, criticality == 3
      Tier 2: 15 <= delta_p% < 35  OR  criticality == 2
      Tier 1: delta_p% < 15  AND  criticality <= 1
    Evaluated most-severe-first so overlapping conditions resolve safely.
    """
    delta_p = state.pressure_drop_pct
    criticality = state.criticality_score or 1
    slope = state.pressure_slope

    if (
        delta_p >= TIER3_DELTA_P_PCT_MIN
        and slope < TIER3_PRESSURE_SLOPE_MAX
        and criticality == TIER3_CRITICALITY_REQUIRED
    ):
        return 3
    if (TIER2_DELTA_P_PCT_MIN <= delta_p < TIER2_DELTA_P_PCT_MAX) or criticality == TIER2_CRITICALITY_TRIGGER:
        return 2
    if delta_p < TIER1_DELTA_P_PCT_MAX and criticality <= TIER1_CRITICALITY_MAX:
        return 1
    # Anything that doesn't cleanly satisfy Tier 1 but also misses the Tier 2/3
    # gates (e.g. large drop but low criticality with a shallow slope) is
    # escalated to Tier 2 by default -- never silently downgraded to Tier 1.
    return 2


def compute_confidence_score(state: ClusterInvestigationState) -> float:
    """
    Weighted confidence score (Section 5.D):
        score = 0.40 * C_telemetry + 0.40 * C_CAMARA + 0.20 * C_trend
    """
    window_len = len(state.window.readings)
    c_telemetry = min(1.0, window_len / EXPECTED_TELEMETRY_WINDOW_LEN)

    if state.api_unavailable:
        c_camara = 0.0
    elif state.camara_reachability_status is not None and state.camara_congestion_level is not None:
        c_camara = 1.0
    else:
        c_camara = 0.5  # partial CAMARA data (e.g. reachability only)

    c_trend = state.trend_r_squared

    score = (
        CONFIDENCE_WEIGHT_TELEMETRY * c_telemetry
        + CONFIDENCE_WEIGHT_CAMARA * c_camara
        + CONFIDENCE_WEIGHT_TREND * c_trend
    )
    return round(max(0.0, min(1.0, score)), 4)


def assess_risk(state: ClusterInvestigationState, topology: TopologyCache) -> ClusterInvestigationState:
    """
    Runs the full Stage 3 pipeline on a cluster that Stage 2 has already
    classified. Instrument faults bypass the risk matrix entirely and their
    telemetry is marked stale (Section 5.C.4); connectivity artifacts get a
    minimal Tier 1 (no physical assessment is meaningful once the reading is
    known to reflect thermal cell degradation rather than the pipe).
    """
    compute_physical_deviations(state)
    assign_segment_metadata(state, topology)

    if state.classification == Classification.CONFIRMED_INSTRUMENT_FAULT:
        state.is_stale_pre_outage_data = True
        state.severity_tier = 1  # maintenance dispatch path, not a physical tier
    elif state.classification == Classification.LIKELY_CONNECTIVITY_ARTIFACT:
        state.severity_tier = 1
    elif state.classification == Classification.INSUFFICIENT_DATA:
        from aia.config import API_UNAVAILABLE_FALLBACK_TIER
        state.severity_tier = API_UNAVAILABLE_FALLBACK_TIER
    else:  # CONFIRMED_ANOMALY
        state.severity_tier = assign_severity_tier(state)

    state.confidence_score = compute_confidence_score(state)
    return state
