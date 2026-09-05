"""
Stage 1 Detection Node.

Applies Z-Score statistical thresholds and the Physics-Informed ML Leak Detector
to filter incoming raw sensor streams.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
import statistics

from aia.models import TelemetryWindow

logger = logging.getLogger("aia.detection")

ML_LEAK_CONFIDENCE_THRESHOLD = 0.75
Z_SCORE_BREACH_THRESHOLD = 3.5


@dataclass
class BaselineStats:
    pressure_mean: float
    pressure_std: float
    flow_mean: float
    flow_std: float


class BaselineStore:
    def __init__(self):
        self._baselines: dict[str, BaselineStats] = {}

    def seed_baseline(self, cluster_id: str, stats: BaselineStats):
        self._baselines[cluster_id] = stats

    def get_baseline(self, cluster_id: str) -> BaselineStats | None:
        return self._baselines.get(cluster_id)


@dataclass
class DetectionResult:
    is_suspicious: bool
    reason: str
    z_p: float = 0.0
    z_q: float = 0.0
    ml_confidence: float = 0.0


def detect_and_learn(
    window: TelemetryWindow,
    baseline_store: BaselineStore,
    leak_detector=None,
    pipe_diameter_mm: float = 200.0,
    pipe_age_years: int = 10,
    pipe_material: str = "HDPE",
) -> DetectionResult:
    readings = window.readings
    if not readings:
        return DetectionResult(is_suspicious=False, reason="No sensor readings in window")

    cluster_id = window.sensor_cluster_id
    baseline = baseline_store.get_baseline(cluster_id)

    # Statistical Z-Scores calculation
    z_p, z_q = 0.0, 0.0
    z_breached = False

    if baseline:
        pressures = [r.pressure_psi for r in readings]
        flows = [r.flow_rate_lps for r in readings]

        p_mean = statistics.mean(pressures)
        q_mean = statistics.mean(flows)

        z_p = (p_mean - baseline.pressure_mean) / max(baseline.pressure_std, 0.1)
        z_q = (q_mean - baseline.flow_mean) / max(baseline.flow_std, 0.1)

        if abs(z_p) >= Z_SCORE_BREACH_THRESHOLD or abs(z_q) >= Z_SCORE_BREACH_THRESHOLD:
            z_breached = True

    # Physics ML Leak Detection
    ml_confidence = 0.0
    ml_suspicious = False

    if leak_detector is not None:
        try:
            if hasattr(leak_detector, "predict_leak_probability"):
                ml_confidence = leak_detector.predict_leak_probability(readings)
            else:
                feats = leak_detector.extract_hydraulic_features(readings)
                proba = leak_detector.predict_proba(feats)
                ml_confidence = float(proba[0][1])

            if ml_confidence >= ML_LEAK_CONFIDENCE_THRESHOLD:
                ml_suspicious = True
        except Exception as err:
            logger.warning("ML prediction failed for %s: %s", cluster_id, err)

    is_suspicious = z_breached or ml_suspicious

    reasons = []
    if z_breached:
        reasons.append(f"Z-score breach (Zp={z_p:.2f}, Zq={z_q:.2f})")
    if ml_suspicious:
        reasons.append(f"Physics ML leak detected (confidence={ml_confidence:.3f})")

    reason = "; ".join(reasons) if is_suspicious else "Normal telemetry"

    return DetectionResult(
        is_suspicious=is_suspicious,
        reason=reason,
        z_p=z_p,
        z_q=z_q,
        ml_confidence=ml_confidence,
    )