"""
Stage 3: Deterministic Risk Assessment & Severity Tiering -- Section 5.C/5.D.

All math lives here in pure Python/NumPy -- the LLM never touches these
calculations (Section 6, "Strict LLM Boundary").

Supports zone-specific threshold profiles: each geographic zone can override
the default tier thresholds defined in config.py. Pipe diameter is factored
into the risk assessment for volume-loss estimation.
"""
from __future__ import annotations

import math

import numpy as np

from aia.config import (
    CONFIDENCE_WEIGHT_CAMARA,
    CONFIDENCE_WEIGHT_TELEMETRY,
    CONFIDENCE_WEIGHT_TREND,
    EXPECTED_TELEMETRY_WINDOW_LEN,
    TIER1_CRITICALITY_MAX,
    TIER2_CRITICALITY_TRIGGER,
    TIER3_CRITICALITY_REQUIRED,
    TIER3_EMERGENCY_DELTA_P_PCT_MIN,
    get_zone_thresholds,
)
from aia.models import Classification, ClusterInvestigationState
from aia.clients.topology import TopologyCache


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
    """Linear regression slope in units per minute using actual timestamps (Section 5.C.2)."""
    n = len(readings)
    if n < 2:
        return 0.0
    t0 = readings[0].timestamp
    minutes = np.array([(r.timestamp - t0).total_seconds() / 60.0 for r in readings])
    if minutes[-1] <= 0:
        return 0.0
    ys = np.array(values, dtype=float)
    slope, _ = np.polyfit(minutes, ys, 1)
    return float(slope)


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


def estimate_volume_loss_lpm(state: ClusterInvestigationState) -> float:
    """
    Estimate the volume of water lost per minute based on the pipe diameter
    and pressure drop. Uses a simplified Torricelli-derived approximation:

        Q_loss ≈ Cd × A_leak × sqrt(2 × g × h)

    where h is derived from the pressure drop (psi → meters of head) and
    A_leak is estimated as a fraction of the pipe cross-section proportional
    to the pressure drop percentage.

    Returns liters per minute (LPM). This is a rough order-of-magnitude
    estimate for operator situational awareness, not a precise hydraulic model.
    """
    diameter_mm = state.pipe_diameter_mm or 200.0
    drop_pct = state.pressure_drop_pct

    # Convert pressure drop from PSI to meters of water head (1 PSI ≈ 0.703m)
    readings = state.window.readings
    baseline_p = readings[0].pressure_psi if readings else 45.0
    pressure_drop_psi = baseline_p * (drop_pct / 100.0)
    head_m = pressure_drop_psi * 0.703

    # Estimate leak area as a fraction of pipe cross-section
    pipe_radius_m = (diameter_mm / 2.0) / 1000.0
    pipe_area_m2 = math.pi * pipe_radius_m ** 2
    leak_fraction = min(drop_pct / 100.0, 1.0)
    leak_area_m2 = pipe_area_m2 * leak_fraction * 0.1  # conservative: 10% of proportional area

    # Torricelli: v = Cd * sqrt(2 * g * h)
    cd = 0.62  # discharge coefficient for a sharp-edged orifice
    g = 9.81
    velocity_mps = cd * math.sqrt(2 * g * max(head_m, 0))
    flow_m3ps = leak_area_m2 * velocity_mps
    return flow_m3ps * 1000.0 * 60.0  # m³/s → L/min


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
        state.pipe_diameter_mm = 200.0
        state.zone_id = None
        return
    state.segment_id = segment.segment_id
    state.criticality_score = segment.criticality_score
    state.proximity_to_reservoir_m = segment.proximity_to_reservoir_m
    state.population_served = segment.population_served
    state.associated_valve_id = segment.associated_valve_id
    state.pipe_diameter_mm = segment.pipe_diameter_mm
    state.zone_id = segment.zone_id


def assign_severity_tier(state: ClusterInvestigationState) -> int:
    """
    Reconciled Risk Tiering Matrix (Section 5.C.3) with zone-specific thresholds.
    Evaluated most-severe-first so overlapping conditions resolve safely.
    """
    delta_p = state.pressure_drop_pct
    criticality = state.criticality_score or 1
    slope = state.pressure_slope

    # Resolve zone-specific thresholds (falls back to defaults if zone unknown)
    thresholds = get_zone_thresholds(state.zone_id)
    t3_delta = thresholds["tier3_delta_p_pct_min"]
    t3_slope = thresholds["tier3_pressure_slope_max"]
    t2_min = thresholds["tier2_delta_p_pct_min"]
    t2_max = thresholds["tier2_delta_p_pct_max"]
    t1_max = thresholds["tier1_delta_p_pct_max"]

    # Emergency override: extreme pressure drop unconditionally triggers Tier 3
    # regardless of criticality.
    if delta_p >= TIER3_EMERGENCY_DELTA_P_PCT_MIN and slope < t3_slope:
        return 3

    # Standard Tier 3: all three conditions required.
    if delta_p >= t3_delta and slope < t3_slope and criticality == TIER3_CRITICALITY_REQUIRED:
        return 3
    if (t2_min <= delta_p < t2_max) or criticality == TIER2_CRITICALITY_TRIGGER:
        return 2
    if delta_p < t1_max and criticality <= TIER1_CRITICALITY_MAX:
        return 1
    # Default to Tier 2 -- never silently downgrade to Tier 1.
    return 2


def compute_confidence_score(state: ClusterInvestigationState) -> float:
    """
    Weighted confidence score (Section 5.D):
        score = 0.40 * C_telemetry + 0.40 * C_CAMARA + 0.20 * C_trend
    """
    window_len = len(state.window.readings)
    c_telemetry = min(1.0, window_len / EXPECTED_TELEMETRY_WINDOW_LEN)

    # Check api_unavailable or specific API failure flags first
    if state.api_unavailable or (state.reachability_api_unavailable and state.congestion_api_unavailable):
        c_camara = 0.0  # Total API failure
    elif state.reachability_api_unavailable or state.congestion_api_unavailable:
        c_camara = 0.5  # One API responded, one failed
    elif state.camara_reachability_status is not None and state.camara_congestion_level is not None:
        c_camara = 1.0  # Both APIs responded successfully
    else:
        c_camara = 0.5  # Partial data

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
    classified. Computes physical deviations, maps segment metadata (including
    zone and pipe diameter), assigns severity tier using zone-specific
    thresholds, and estimates volume loss for operator situational awareness.
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
        state.estimated_volume_loss_lpm = estimate_volume_loss_lpm(state)

    state.confidence_score = compute_confidence_score(state)
    return state
