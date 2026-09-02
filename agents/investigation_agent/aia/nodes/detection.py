"""
Stage 1: Anomaly Detection (Deterministic + Pre-trained ML) -- Section 5.A.

Dual-layer filter run against 100% of incoming telemetry:
  1. Deterministic Z-score / sharp-deviation floor check (never
     temperature-adjusted -- the "Safety Separation Rule").
  2. Pre-trained Random Forest classifier, trained on physics-inspired
     synthetic data (pressure slope, flow surge, P-Q correlation, etc.).

Either layer flagging a window is sufficient to promote it to Stage 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from aia.config import (
    INSTANT_FLOW_SURGE_PCT_FLOOR,
    INSTANT_PRESSURE_DROP_PCT_FLOOR,
    Z_SCORE_THRESHOLD,
)
from aia.models import TelemetryWindow


@dataclass
class BaselineStats:
    """Historical per-cluster baseline (mean/std) used for the Z-score check."""
    pressure_mean: float
    pressure_std: float
    flow_mean: float
    flow_std: float


@dataclass
class DetectionResult:
    is_suspicious: bool
    z_score_pressure: float
    z_score_flow: float
    ml_confidence: Optional[float]
    reason: str


class BaselineStore:
    """
    Tracks a rolling per-cluster baseline used for Z-score calculation.
    Healthy windows are fed back to update the baseline over time.
    """

    def __init__(self):
        self._baselines: dict[str, BaselineStats] = {}
        self._history: dict[str, list[tuple[float, float]]] = {}

    def seed_baseline(self, sensor_cluster_id: str, stats: BaselineStats) -> None:
        self._baselines[sensor_cluster_id] = stats

    def get_baseline(self, sensor_cluster_id: str) -> Optional[BaselineStats]:
        return self._baselines.get(sensor_cluster_id)

    def update_baseline(self, sensor_cluster_id: str, window: TelemetryWindow) -> None:
        """Update the rolling baseline with readings from a healthy window."""
        hist = self._history.setdefault(sensor_cluster_id, [])
        for r in window.readings:
            hist.append((r.pressure_psi, r.flow_rate_lps))

        # Keep a rolling window of 200 readings max
        if len(hist) > 200:
            hist[:] = hist[-200:]

        arr = np.array(hist)
        self._baselines[sensor_cluster_id] = BaselineStats(
            pressure_mean=float(np.mean(arr[:, 0])),
            pressure_std=float(np.std(arr[:, 0])),
            flow_mean=float(np.mean(arr[:, 1])),
            flow_std=float(np.std(arr[:, 1])),
        )


def _linreg_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    xs = np.arange(n, dtype=float)
    ys = np.array(values, dtype=float)
    slope, _ = np.polyfit(xs, ys, 1)
    return float(slope)


def compute_z_scores(window: TelemetryWindow, baseline: BaselineStats) -> tuple[float, float]:
    """Z-score of the most recent reading vs. the cluster's historical baseline."""
    current = window.readings[-1]
    z_p = (
        (current.pressure_psi - baseline.pressure_mean) / baseline.pressure_std
        if baseline.pressure_std > 0
        else 0.0
    )
    z_q = (
        (current.flow_rate_lps - baseline.flow_mean) / baseline.flow_std
        if baseline.flow_std > 0
        else 0.0
    )
    return z_p, z_q


def check_sharp_deviation(window: TelemetryWindow) -> tuple[bool, str]:
    """
    Deterministic safety-floor check: an instant pressure drop >= 15% or flow
    surge >= 20% within the rolling window. This check is NEVER temperature-adjusted.
    """
    readings = window.readings
    if len(readings) < 2:
        return False, ""
    baseline_p = readings[0].pressure_psi
    baseline_q = readings[0].flow_rate_lps
    current_p = readings[-1].pressure_psi
    current_q = readings[-1].flow_rate_lps

    drop_pct = ((baseline_p - current_p) / baseline_p * 100.0) if baseline_p else 0.0
    surge_pct = ((current_q - baseline_q) / baseline_q * 100.0) if baseline_q else 0.0

    reasons = []
    if drop_pct >= INSTANT_PRESSURE_DROP_PCT_FLOOR:
        reasons.append(f"pressure drop {drop_pct:.1f}% >= {INSTANT_PRESSURE_DROP_PCT_FLOOR}% floor")
    if surge_pct >= INSTANT_FLOW_SURGE_PCT_FLOOR:
        reasons.append(f"flow surge {surge_pct:.1f}% >= {INSTANT_FLOW_SURGE_PCT_FLOOR}% floor")

    return (len(reasons) > 0), "; ".join(reasons)


def run_random_forest(
    window: TelemetryWindow,
    leak_detector,
    pipe_diameter_mm: float = 200.0,
    pipe_age_years: int = 10,
    pipe_material: str = "HDPE",
) -> tuple[bool, float]:
    """
    Score the window with the pre-trained Random Forest model.
    Returns (is_leak, confidence_probability).
    """
    pressures = [r.pressure_psi for r in window.readings]
    flows = [r.flow_rate_lps for r in window.readings]
    temps = [r.ambient_temp_c for r in window.readings]

    # Use the timestamp of the first reading to get hour_of_day
    hour = window.readings[0].timestamp.hour if window.readings else 12

    return leak_detector.predict(
        pressures=pressures,
        flows=flows,
        temps=temps,
        pipe_diameter_mm=pipe_diameter_mm,
        pipe_age_years=pipe_age_years,
        pipe_material=pipe_material,
        hour_of_day=hour,
    )


def detect(
    window: TelemetryWindow,
    baseline_store: BaselineStore,
    leak_detector=None,
    pipe_diameter_mm: float = 200.0,
    pipe_age_years: int = 10,
    pipe_material: str = "HDPE",
) -> DetectionResult:
    """
    Run the full dual-layer Stage 1 detection for a single cluster's window.
    Layer 1: Deterministic Z-score + sharp deviation floor.
    Layer 2: Pre-trained Random Forest classifier.
    Returns a DetectionResult; `is_suspicious=True` promotes the cluster to Stage 2.
    """
    reasons: list[str] = []
    z_p = z_q = 0.0
    ml_confidence: Optional[float] = None

    # Layer 1: Z-score check
    baseline = baseline_store.get_baseline(window.sensor_cluster_id)
    if baseline is not None:
        z_p, z_q = compute_z_scores(window, baseline)
        if abs(z_p) >= Z_SCORE_THRESHOLD or abs(z_q) >= Z_SCORE_THRESHOLD:
            reasons.append(
                f"Z-score breach (Zp={z_p:.2f}, Zq={z_q:.2f}, threshold={Z_SCORE_THRESHOLD})"
            )

    # Layer 1b: Sharp deviation floor
    sharp, sharp_reason = check_sharp_deviation(window)
    if sharp:
        reasons.append(sharp_reason)

    # Layer 2: Pre-trained Random Forest
    if leak_detector is not None:
        is_ml_leak, ml_confidence = run_random_forest(
            window, leak_detector,
            pipe_diameter_mm, pipe_age_years, pipe_material,
        )
        if is_ml_leak:
            reasons.append(f"Random Forest leak detected (confidence={ml_confidence:.3f})")

    is_suspicious = len(reasons) > 0
    return DetectionResult(
        is_suspicious=is_suspicious,
        z_score_pressure=z_p,
        z_score_flow=z_q,
        ml_confidence=ml_confidence,
        reason="; ".join(reasons) if reasons else "within normal operational bounds",
    )


def detect_and_learn(
    window: TelemetryWindow,
    baseline_store: BaselineStore,
    leak_detector=None,
    pipe_diameter_mm: float = 200.0,
    pipe_age_years: int = 10,
    pipe_material: str = "HDPE",
) -> DetectionResult:
    """
    Detect first, then only feed *healthy* windows back into the baseline
    so a genuine leak can't poison the baseline statistics.
    """
    result = detect(window, baseline_store, leak_detector,
                    pipe_diameter_mm, pipe_age_years, pipe_material)
    if not result.is_suspicious:
        baseline_store.update_baseline(window.sensor_cluster_id, window)
    return result
