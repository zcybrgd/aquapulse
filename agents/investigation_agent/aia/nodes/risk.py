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

    Returns liters per minute (LPM). Rough order-of-magnitude estimate for operator
    situational awareness.
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
    leak_area_m2 = pipe_area_m2 * leak_fraction * 0.1  # 10% of proportional area

    # Torricelli equation
    cd = 0.62
    g = 9.81
    velocity_mps = cd * math.sqrt(2 * g * max(head_m, 0))
    flow_m3ps = leak_area_m2 * velocity_mps
    return flow_m3ps * 1000.0 * 60.0  # m³/s → L/min


def assign_segment_metadata(state: ClusterInvestigationState, topology: TopologyCache) -> None:
    """Section 5.C.1: map the cluster to its physical segment via the local topology cache."""
    segment = topology.get_segment_for_cluster(state.sensor_cluster_id)
    if segment is None:
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
    Evaluated hierarchically so physical severity and asset criticality are balanced safely.
    """
    delta_p = state.pressure_drop_pct
    criticality = state.criticality_score or 1
    slope = state.pressure_slope

    # Resolve zone-specific thresholds
    thresholds = get_zone_thresholds(state.zone_id)
    t3_delta = thresholds.get("tier3_delta_p_pct_min", 25.0)
    t3_slope = thresholds.get("tier3_pressure_slope_max", -1.0)
    t2_min = thresholds.get("tier2_delta_p_pct_min", 10.0)

    # 1. Tier 3 (High Risk / Immediate Intervention Required):
    # - Extreme pressure drop (>= 50%) OR
    # - Major pressure drop (>= t3_delta) on medium/high criticality assets (criticality >= 2) OR
    # - Major pressure drop (>= t3_delta) with rapid pressure drop rate (slope < t3_slope)
    if delta_p >= TIER3_EMERGENCY_DELTA_P_PCT_MIN:
        return 3
    if delta_p >= t3_delta and (criticality >= 2 or slope < t3_slope):
        return 3

    # 2. Tier 2 (Moderate Anomaly / Action Required):
    # - Moderate pressure drop (>= t2_min) OR
    # - Significant pressure drop (>= t3_delta) on low-criticality asset (criticality == 1) OR
    # - High-criticality asset (criticality == 3) experiencing any non-minor deviation
    if delta_p >= t2_min or delta_p >= t3_delta or criticality == 3:
        return 2

    # 3. Tier 1 (Low Risk / Minor Deviation / Log Only):
    # - Minor pressure drop (< t2_min) on low or medium criticality assets
    return 1


def compute_confidence_score(state: ClusterInvestigationState) -> float:
    """
    Weighted confidence score (Section 5.D):
        score = 0.40 * C_telemetry + 0.40 * C_CAMARA + 0.20 * C_trend
    """
    window_len = len(state.window.readings)
    c_telemetry = min(1.0, window_len / EXPECTED_TELEMETRY_WINDOW_LEN)

    if state.api_unavailable or (state.reachability_api_unavailable and state.congestion_api_unavailable):
        c_camara = 0.0
    elif state.reachability_api_unavailable or state.congestion_api_unavailable:
        c_camara = 0.5
    elif state.camara_reachability_status is not None and state.camara_congestion_level is not None:
        c_camara = 1.0
    else:
        c_camara = 0.5

    c_trend = state.trend_r_squared

    score = (
        CONFIDENCE_WEIGHT_TELEMETRY * c_telemetry
        + CONFIDENCE_WEIGHT_CAMARA * c_camara
        + CONFIDENCE_WEIGHT_TREND * c_trend
    )
    return round(max(0.0, min(1.0, score)), 4)


def assess_risk(state: ClusterInvestigationState, topology: TopologyCache) -> ClusterInvestigationState:
    """
    Runs the full Stage 3 pipeline on a cluster that Stage 2 has already classified.
    Computes physical deviations, maps segment metadata, assigns severity tier,
    and estimates volume loss for operator situational awareness.
    """
    compute_physical_deviations(state)
    assign_segment_metadata(state, topology)

    if state.classification == Classification.CONFIRMED_INSTRUMENT_FAULT:
        state.is_stale_pre_outage_data = True
        state.severity_tier = 1
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