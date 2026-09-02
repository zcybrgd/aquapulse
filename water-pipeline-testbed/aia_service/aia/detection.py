"""
Stage 1: Anomaly Detection (Deterministic & Bootstrap ML) -- Section 5.A.

Dual-layer filter run against 100% of incoming telemetry:
  1. Deterministic Z-score / sharp-deviation floor check (never
     temperature-adjusted -- the "Safety Separation Rule").
  2. Lightweight unsupervised Isolation Forest, bootstrapped from the
     cluster's own early operational data, with a temperature-adaptive
     noise tolerance applied ONLY to this ML layer.

Either layer flagging a window is sufficient to promote it to Stage 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from aia.config import (
    INSTANT_FLOW_SURGE_PCT_FLOOR,
    INSTANT_PRESSURE_DROP_PCT_FLOOR,
    ISO_FOREST_CONTAMINATION,
    ISO_FOREST_MIN_BOOTSTRAP_SAMPLES,
    ISO_FOREST_N_ESTIMATORS,
    ISO_FOREST_RANDOM_STATE,
    ML_TEMP_ADAPTATION_TAU_SHIFT,
    ML_TEMP_ADAPTATION_THRESHOLD_C,
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
    iso_forest_score: Optional[float]
    reason: str


class BaselineStore:
    """
    Tracks a rolling per-cluster baseline used for Z-score calculation, and
    accumulates the early-operational bootstrap window used to fit each
    cluster's Isolation Forest model (Section 5.A.2).
    """

    def __init__(self, min_bootstrap_samples: int = ISO_FOREST_MIN_BOOTSTRAP_SAMPLES):
        self._baselines: dict[str, BaselineStats] = {}
        self._history: dict[str, list[tuple[float, float, float]]] = {}
        self._models: dict[str, IsolationForest] = {}
        self._min_bootstrap_samples = min_bootstrap_samples

    def seed_baseline(self, sensor_cluster_id: str, stats: BaselineStats) -> None:
        self._baselines[sensor_cluster_id] = stats

    def get_baseline(self, sensor_cluster_id: str) -> Optional[BaselineStats]:
        return self._baselines.get(sensor_cluster_id)

    def record_and_maybe_fit(self, sensor_cluster_id: str, window: TelemetryWindow) -> None:
        """
        Feed the newest healthy reading into the bootstrap history; (re)fit
        once enough data exists.

        Only `window.readings[-1]` is appended (not the whole window). A
        streaming window is a rolling view over recent readings -- most of
        it overlaps with the window seen on the previous call. Appending
        every reading in the window each time would re-insert the same
        near-duplicate samples repeatedly as they slide through the window,
        collapsing the Isolation Forest's learned variance and making its
        decision boundary artificially tight (ordinary noise starts
        reading as anomalous). Appending only the newest sample keeps the
        bootstrap history representative of the cluster's true operating
        distribution.
        """
        hist = self._history.setdefault(sensor_cluster_id, [])
        r = window.readings[-1]
        hist.append((r.pressure_psi, r.flow_rate_lps, r.ambient_temp_c))
        if len(hist) >= self._min_bootstrap_samples:
            X = np.array(hist)
            model = IsolationForest(
                n_estimators=ISO_FOREST_N_ESTIMATORS,
                contamination=ISO_FOREST_CONTAMINATION,
                random_state=ISO_FOREST_RANDOM_STATE,
            )
            model.fit(X)
            self._models[sensor_cluster_id] = model

    def get_model(self, sensor_cluster_id: str) -> Optional[IsolationForest]:
        return self._models.get(sensor_cluster_id)


def _linreg_slope(values: list[float]) -> float:
    """Slope of `values` over index (used generically; Stage 3 has the psi/min version)."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = np.arange(n, dtype=float)
    ys = np.array(values, dtype=float)
    slope, _ = np.polyfit(xs, ys, 1)
    return float(slope)


def compute_z_scores(window: TelemetryWindow, baseline: BaselineStats) -> tuple[float, float]:
    """Z-score of the most recent reading vs. the cluster's historical baseline (Section 5.A.1)."""
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
    surge >= 20% within the rolling window (Section 1 / 5.A.1). This check is
    NEVER temperature-adjusted.
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


def run_isolation_forest(
    window: TelemetryWindow, model: IsolationForest
) -> tuple[bool, float]:
    """
    Score the latest reading with the cluster's bootstrapped Isolation Forest.
    Applies temperature-adaptive noise tolerance to the decision boundary only
    (never to the deterministic Z-score/sharp-deviation floors above).
    """
    current = window.readings[-1]
    x = np.array([[current.pressure_psi, current.flow_rate_lps, current.ambient_temp_c]])
    raw_score = float(model.decision_function(x)[0])  # >0 normal-ish, <0 anomaly-ish
    prediction = int(model.predict(x)[0])  # 1 = normal, -1 = anomaly

    tau_shift = 0.0
    if current.ambient_temp_c >= ML_TEMP_ADAPTATION_THRESHOLD_C:
        tau_shift = ML_TEMP_ADAPTATION_TAU_SHIFT

    is_anomaly = (prediction == -1) and (raw_score < -tau_shift)
    return is_anomaly, raw_score


def detect(
    window: TelemetryWindow,
    baseline_store: BaselineStore,
) -> DetectionResult:
    """
    Run the full dual-layer Stage 1 detection for a single cluster's window.
    Returns a DetectionResult; `is_suspicious=True` promotes the cluster to
    Stage 2 investigation.
    """
    reasons: list[str] = []
    z_p = z_q = 0.0
    iso_score: Optional[float] = None

    baseline = baseline_store.get_baseline(window.sensor_cluster_id)
    if baseline is not None:
        z_p, z_q = compute_z_scores(window, baseline)
        if abs(z_p) >= Z_SCORE_THRESHOLD or abs(z_q) >= Z_SCORE_THRESHOLD:
            reasons.append(
                f"Z-score breach (Zp={z_p:.2f}, Zq={z_q:.2f}, threshold={Z_SCORE_THRESHOLD})"
            )

    sharp, sharp_reason = check_sharp_deviation(window)
    if sharp:
        reasons.append(sharp_reason)

    model = baseline_store.get_model(window.sensor_cluster_id)
    if model is not None:
        is_ml_anomaly, iso_score = run_isolation_forest(window, model)
        if is_ml_anomaly:
            reasons.append(f"Isolation Forest anomaly (score={iso_score:.3f})")

    # Always feed the (pre-decision) window into the bootstrap history so the
    # model keeps improving; callers typically do this only for confirmed-
    # healthy windows in production to avoid poisoning the baseline with
    # anomalies -- see `detect_and_learn` below for that policy.

    is_suspicious = len(reasons) > 0
    return DetectionResult(
        is_suspicious=is_suspicious,
        z_score_pressure=z_p,
        z_score_flow=z_q,
        iso_forest_score=iso_score,
        reason="; ".join(reasons) if reasons else "within normal operational bounds",
    )


def detect_and_learn(window: TelemetryWindow, baseline_store: BaselineStore) -> DetectionResult:
    """
    Convenience wrapper matching the Stage 1 pipeline behavior: detect first,
    then only feed *healthy* windows back into the bootstrap history so a
    genuine leak can't poison the model it's about to be judged against.
    """
    result = detect(window, baseline_store)
    if not result.is_suspicious:
        baseline_store.record_and_maybe_fit(window.sensor_cluster_id, window)
    return result
