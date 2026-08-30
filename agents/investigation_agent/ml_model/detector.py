"""
Unified anomaly detection pipeline — called by the investigation agent.

This is the main entry point for Stage 1.  For each incoming sensor reading:

  1. Run deterministic checks (Z-Score, boundary violations)
  2. Run Isolation Forest scoring (loaded from pretrained model)
  3. Fuse results: SUSPICIOUS if ANY layer flags it
  4. Return a DetectionResult

Public API:
  AnomalyDetector(model_path, scaler_path)
  AnomalyDetector.evaluate(reading: SensorReading) -> DetectionResult
  AnomalyDetector.evaluate_batch(readings: list)   -> list[DetectionResult]
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import config
from .model import AnomalyModel
from .schemas import DetectionResult, SensorReading


class AnomalyDetector:
    """Dual-layer anomaly detection: deterministic Z-scores + Isolation Forest ML.

    Layer 1 (Deterministic):
        - Z-score checks on pressure and flow rate against baseline statistics.
        - Boundary violation if Z >= threshold.

    Layer 2 (ML):
        - Isolation Forest scores the reading.
        - Anomaly if score < 0 (sklearn convention).

    Fusion:
        - SUSPICIOUS if ANY layer flags the reading.
    """

    def __init__(
        self,
        model_path: Path | str | None = None,
        scaler_path: Path | str | None = None,
        baselines: dict | None = None,
    ) -> None:
        """Initialise the detector with a pre-trained model.

        Parameters
        ----------
        model_path : Path or str, optional
            Path to the saved Isolation Forest model.
        scaler_path : Path or str, optional
            Path to the saved StandardScaler.
        baselines : dict, optional
            Baseline statistics for Z-score checks. If None, uses
            defaults from config.py.
        """
        # Load pre-trained ML model
        self._model = AnomalyModel.from_pretrained(model_path, scaler_path)

        # Baseline statistics for Z-score layer
        self._baselines = baselines or {
            "pressure_mean": config.BASELINE_PRESSURE_MEAN,
            "pressure_std": config.BASELINE_PRESSURE_STD,
            "flow_mean": config.BASELINE_FLOW_MEAN,
            "flow_std": config.BASELINE_FLOW_STD,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate(self, reading: SensorReading) -> DetectionResult:
        """Evaluate a single sensor reading through the dual-layer pipeline.

        Parameters
        ----------
        reading : SensorReading
            Validated incoming sensor telemetry.

        Returns
        -------
        DetectionResult
            Structured detection result with verdict, trigger, and details.
        """
        # --- Layer 1: Deterministic Z-Score Checks ---
        z_pressure = self._compute_z_score(
            reading.pressure_bar,
            self._baselines["pressure_mean"],
            self._baselines["pressure_std"],
        )
        z_flow = self._compute_z_score(
            reading.flow_rate_lps,
            self._baselines["flow_mean"],
            self._baselines["flow_std"],
        )

        z_scores = {"pressure": round(z_pressure, 4), "flow_rate": round(z_flow, 4)}

        z_score_flagged = (
            abs(z_pressure) >= config.Z_SCORE_THRESHOLD
            or abs(z_flow) >= config.Z_SCORE_THRESHOLD
        )

        # --- Layer 2: ML Isolation Forest Scoring ---
        feature_vector = self._reading_to_features(reading)
        ml_score = float(self._model.score(feature_vector)[0])
        raw_pred = self._model.predict(feature_vector)[0]
        ml_flagged = raw_pred == -1  # -1 = anomaly in sklearn

        # --- Fusion: ANY flag → SUSPICIOUS ---
        is_suspicious = z_score_flagged or ml_flagged

        # Determine trigger source
        if z_score_flagged and ml_flagged:
            trigger = "combined"
        elif z_score_flagged:
            trigger = "z_score"
        elif ml_flagged:
            trigger = "ml_model"
        else:
            trigger = "none"

        # Build explanation
        details = self._build_explanation(
            reading, z_scores, z_score_flagged, ml_score, ml_flagged, trigger
        )

        return DetectionResult(
            sensor_id=reading.sensor_id,
            timestamp=reading.timestamp,
            verdict="suspicious" if is_suspicious else "normal",
            trigger=trigger,
            ml_score=round(ml_score, 6),
            z_scores=z_scores,
            details=details,
        )

    def evaluate_batch(self, readings: list[SensorReading]) -> list[DetectionResult]:
        """Evaluate a batch of sensor readings.

        Parameters
        ----------
        readings : list[SensorReading]
            List of validated sensor readings.

        Returns
        -------
        list[DetectionResult]
            Detection results for each reading.
        """
        return [self.evaluate(r) for r in readings]

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_z_score(value: float, mean: float, std: float) -> float:
        """Compute Z-score for a single value against baseline statistics."""
        if std == 0:
            return 0.0
        return (value - mean) / std

    def _reading_to_features(self, reading: SensorReading) -> np.ndarray:
        """Convert a SensorReading into a feature vector for the ML model.

        Feature order must match ``config.ENGINEERED_FEATURE_COLUMNS``:
        [Pressure, Flow Rate, Temperature, pressure_flow_ratio, hour_of_day]
        """
        pressure = reading.pressure_bar
        flow_rate = reading.flow_rate_lps
        temperature = reading.temperature_c
        pressure_flow_ratio = pressure / flow_rate if flow_rate > 0 else 0.0

        # Extract hour from timestamp string
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(reading.timestamp)
            hour = ts.hour
        except (ValueError, TypeError):
            hour = 0

        features = np.array(
            [[pressure, flow_rate, temperature, pressure_flow_ratio, hour]],
            dtype=np.float64,
        )
        return features

    @staticmethod
    def _build_explanation(
        reading: SensorReading,
        z_scores: dict[str, float],
        z_flagged: bool,
        ml_score: float,
        ml_flagged: bool,
        trigger: str,
    ) -> str:
        """Build a human-readable explanation of the detection result."""
        parts: list[str] = []

        parts.append(
            f"Sensor {reading.sensor_id} at {reading.timestamp}: "
            f"P={reading.pressure_bar:.2f} bar, "
            f"Q={reading.flow_rate_lps:.2f} L/s, "
            f"T={reading.temperature_c:.1f}°C."
        )

        if z_flagged:
            flagged_features = []
            if abs(z_scores["pressure"]) >= config.Z_SCORE_THRESHOLD:
                flagged_features.append(
                    f"pressure Z={z_scores['pressure']:.2f}"
                )
            if abs(z_scores["flow_rate"]) >= config.Z_SCORE_THRESHOLD:
                flagged_features.append(
                    f"flow_rate Z={z_scores['flow_rate']:.2f}"
                )
            parts.append(
                f"Z-score threshold exceeded: {', '.join(flagged_features)} "
                f"(threshold=±{config.Z_SCORE_THRESHOLD})."
            )

        if ml_flagged:
            parts.append(
                f"Isolation Forest flagged anomaly (score={ml_score:.4f})."
            )

        if trigger == "none":
            parts.append("All checks passed — reading is normal.")

        return " ".join(parts)
