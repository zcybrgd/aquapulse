
from __future__ import annotations

import logging
import os
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger("ml_model.inference")

_ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")


class LeakDetector:

    def __init__(self, artifacts_dir: str = _ARTIFACTS_DIR):
        model_path = os.path.join(artifacts_dir, "best_model.joblib")
        preprocessor_path = os.path.join(artifacts_dir, "preprocessor.joblib")

        if not os.path.exists(model_path) or not os.path.exists(preprocessor_path):
            raise FileNotFoundError(
                f"Model artifacts not found in {artifacts_dir}. "
                "Run `python -m ml_model.train` first."
            )

        self._model = joblib.load(model_path)
        self._preprocessor = joblib.load(preprocessor_path)
        logger.info("LeakDetector loaded from %s", artifacts_dir)

    @staticmethod
    def compute_features_from_readings(
        pressures: list[float],
        flows: list[float],
        temps: list[float],
        pipe_diameter_mm: float = 200.0,
        pipe_age_years: int = 10,
        pipe_material: str = "HDPE",
        hour_of_day: int = 12,
    ) -> dict:

        p = np.array(pressures)
        q = np.array(flows)
        t = np.array(temps)
        n = len(p)
        xs = np.arange(n, dtype=float)

        p_mean = float(np.mean(p))
        p_std = float(np.std(p))
        p_min = float(np.min(p))
        p_max = float(np.max(p))
        p_first = max(float(p[0]), 0.01)
        p_last = float(p[-1])
        p_drop_pct = (p_first - p_last) / p_first * 100.0
        p_slope = float(np.polyfit(xs, p, 1)[0]) if n >= 2 else 0.0
        p_rolling_std_5 = float(np.std(p[-5:])) if n >= 5 else p_std
        p_jitter = float(np.std(np.diff(p))) if n >= 2 else 0.0

        q_mean = float(np.mean(q))
        q_std = float(np.std(q))
        q_first = max(float(q[0]), 0.01)
        q_last = float(q[-1])
        q_surge_pct = (q_last - q_first) / q_first * 100.0
        q_slope = float(np.polyfit(xs, q, 1)[0]) if n >= 2 else 0.0

        if p_std > 1e-6 and q_std > 1e-6:
            pq_corr = float(np.corrcoef(p, q)[0, 1])
        else:
            pq_corr = 0.0

        t_mean = float(np.mean(t))
        t_max = float(np.max(t))
        zero_count = int(np.sum(p == 0.0))

        return {
            "p_mean": round(p_mean, 2),
            "p_std": round(p_std, 4),
            "p_min": round(p_min, 2),
            "p_max": round(p_max, 2),
            "p_drop_pct": round(p_drop_pct, 2),
            "p_slope": round(p_slope, 4),
            "p_rolling_std_5": round(p_rolling_std_5, 4),
            "p_jitter": round(p_jitter, 4),
            "q_mean": round(q_mean, 2),
            "q_std": round(q_std, 4),
            "q_surge_pct": round(q_surge_pct, 2),
            "q_slope": round(q_slope, 4),
            "pq_corr": round(pq_corr, 4),
            "t_mean": round(t_mean, 1),
            "t_max": round(t_max, 1),
            "zero_count": zero_count,
            "pipe_diameter_mm": pipe_diameter_mm,
            "pipe_age_years": pipe_age_years,
            "pipe_material": pipe_material,
            "hour_of_day": hour_of_day,
        }

    def predict(
        self,
        pressures: list[float],
        flows: list[float],
        temps: list[float],
        pipe_diameter_mm: float = 200.0,
        pipe_age_years: int = 10,
        pipe_material: str = "HDPE",
        hour_of_day: int = 12,
    ) -> tuple[bool, float]:

        import pandas as pd

        features = self.compute_features_from_readings(
            pressures, flows, temps,
            pipe_diameter_mm, pipe_age_years, pipe_material, hour_of_day,
        )
        df = pd.DataFrame([features])

        X = self._preprocessor.transform(df)
        proba = self._model.predict_proba(X)[0]  # [P(normal), P(leak)]
        leak_proba = float(proba[1])
        is_leak = leak_proba >= 0.5

        return is_leak, leak_proba
