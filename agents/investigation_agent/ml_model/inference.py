"""
Physics-Informed Hydraulic Leak Detector.

Combines hydro-dynamic physical conservation laws (dP/dt, dQ/dt, pressure drop ratio)
with an Isolation Forest trained on realistic operational noise distributions.
"""

from __future__ import annotations

import logging
import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("aia.ml_model")


class LeakDetector:
    def __init__(self, model_path: str | None = None):
        if model_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_dir, "artifacts", "best_model.joblib")

        self.model_path = model_path
        self.iso_forest: IsolationForest | None = None
        self._load_or_train_model()

    def _load_or_train_model(self) -> None:
        """Loads saved model artifact or trains a calibrated Isolation Forest."""
        if os.path.exists(self.model_path):
            try:
                loaded = joblib.load(self.model_path)
                if isinstance(loaded, IsolationForest):
                    self.iso_forest = loaded
                    logger.info("Loaded Physics Isolation Forest from %s", self.model_path)
                    return
            except Exception as err:
                logger.warning("Could not load joblib artifact (%s). Re-calibrating...", err)

        self._fit_physics_baseline()

    def _fit_physics_baseline(self) -> None:
        """Trains Isolation Forest on realistic operational distributions including sensor noise."""
        np.random.seed(42)
        # 2000 normal operational samples incorporating standard simulator noise (std up to 0.80)
        dp_dt = np.random.normal(0.0, 0.40, 2000)
        dq_dt = np.random.normal(0.0, 0.50, 2000)
        divergence = dp_dt * dq_dt
        p_std = np.random.uniform(0.10, 0.80, 2000)
        q_std = np.random.uniform(0.10, 0.80, 2000)

        X_normal = np.column_stack([dp_dt, dq_dt, divergence, p_std, q_std])

        # Train Isolation Forest with low contamination threshold
        self.iso_forest = IsolationForest(contamination=0.01, random_state=42, n_estimators=100)
        self.iso_forest.fit(X_normal)

        # Save model artifact
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.iso_forest, self.model_path)
        logger.info("Calibrated and saved Physics Isolation Forest to %s", self.model_path)

    @staticmethod
    def extract_hydraulic_features(readings: list) -> np.ndarray:
        """Extracts hydro-dynamic physical features from time-series window readings."""
        if not readings or len(readings) < 2:
            return np.array([[0.0, 0.0, 0.0, 0.5, 0.5]])

        pressures = [getattr(r, "pressure_psi", 0.0) for r in readings]
        flows = [getattr(r, "flow_rate_lps", 0.0) for r in readings]

        # Slopes (dP/dt and dQ/dt) across the window
        dp_dt = float(pressures[-1] - pressures[0])
        dq_dt = float(flows[-1] - flows[0])

        # Hydraulic Divergence: Pressure drop coupled with flow surge/change
        divergence = dp_dt * dq_dt

        # Feature Volatility
        p_std = float(np.std(pressures)) if len(pressures) > 1 else 0.5
        q_std = float(np.std(flows)) if len(flows) > 1 else 0.5

        return np.array([[dp_dt, dq_dt, divergence, p_std, q_std]])

    def predict_leak_probability(self, readings_or_features) -> float:
        """
        Calculates physical leak confidence score (0.00 to 1.00).
        - Normal telemetry noise: 0.00 to 0.10
        - Physical pipe leak/burst: >0.85
        """
        if isinstance(readings_or_features, list):
            feats = self.extract_hydraulic_features(readings_or_features)
        elif isinstance(readings_or_features, np.ndarray):
            feats = readings_or_features if readings_or_features.ndim == 2 else readings_or_features.reshape(1, -1)
        else:
            return 0.0

        if feats.shape[1] > 5:
            feats = feats[:, :5]

        dp_dt, dq_dt, divergence, p_std, q_std = feats[0]

        # 1. Evaluate Hydrodynamic Leak Rules
        # Major leak signature: Rapid pressure collapse (dP/dt <= -2.5) paired with flow change or high volatility
        is_major_leak = (dp_dt <= -2.5) and (dq_dt >= 1.5 or p_std > 1.2)
        is_moderate_leak = (dp_dt <= -1.8) or (p_std > 1.8 and q_std > 1.8)

        # 2. Compute Isolation Forest Anomaly Score
        raw_score = self.iso_forest.score_samples(feats)[0]  # Normal data ~ -0.42 to -0.52
        
        # Sigmoid scaling for outlier distance
        iso_prob = 1.0 / (1.0 + np.exp(12.0 * (raw_score + 0.62)))

        # 3. Apply Physical Guardrails
        if is_major_leak:
            final_prob = max(0.90, iso_prob)
        elif is_moderate_leak:
            final_prob = max(0.75, iso_prob)
        elif abs(dp_dt) < 1.2 and abs(dq_dt) < 1.5 and p_std < 1.0 and q_std < 1.0:
            # Baseline background noise: Cap confidence near zero
            final_prob = min(0.05, iso_prob)
        else:
            final_prob = float(iso_prob)

        return float(np.clip(final_prob, 0.0, 1.0))

    def predict_proba(self, X) -> np.ndarray:
        """Scikit-learn compatible predict_proba interface."""
        if isinstance(X, list):
            p = self.predict_leak_probability(X)
            return np.array([[1.0 - p, p]])

        if isinstance(X, np.ndarray):
            if X.ndim == 2 and X.shape[0] > 1:
                probs = []
                for row in X:
                    p = self.predict_leak_probability(row.reshape(1, -1))
                    probs.append([1.0 - p, p])
                return np.array(probs)

            p = self.predict_leak_probability(X)
            return np.array([[1.0 - p, p]])

        return np.array([[0.95, 0.05]])