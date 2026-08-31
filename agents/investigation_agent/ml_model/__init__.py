"""
AquaPulse — ML Anomaly Detection Module
========================================

Stage 1 of the Anomaly Investigation Agent (AIA).
Detects water leakage using dual-layer detection:
  - Layer 1: Deterministic Z-score checks
  - Layer 2: Isolation Forest ML model

Trained on: water_leak_detection_1000_rows.csv
Algorithm:  Isolation Forest (scikit-learn)

Module Structure
----------------
::

    ml_model/
    ├── __init__.py        # Public API (this file)
    ├── config.py          # Thresholds, paths, hyperparameters
    ├── schemas.py         # Pydantic v2 I/O contracts
    ├── preprocessing.py   # Data loading, cleaning, feature engineering
    ├── model.py           # Isolation Forest (train / predict / save / load)
    ├── detector.py        # Unified pipeline: deterministic checks + ML scoring
    ├── train.py           # Training entrypoint script
    ├── artifacts/         # Saved model, scaler, and baselines
    └── data/              # Training dataset (CSV)

Usage (Inference)
-----------------
::

    from agents.investigation_agent.ml_model import AnomalyDetector, SensorReading

    detector = AnomalyDetector()
    reading = SensorReading(
        sensor_id="S001",
        timestamp="2024-01-01T00:00:00",
        pressure_bar=3.5,
        flow_rate_lps=80.0,
        temperature_c=22.0,
    )
    result = detector.evaluate(reading)
    print(result.verdict)  # "normal" or "suspicious"

Usage (Training)
----------------
::

    python -m agents.investigation_agent.ml_model.train
"""

from .detector import AnomalyDetector
from .schemas import DetectionResult, SensorReading

__all__ = [
    "AnomalyDetector",
    "SensorReading",
    "DetectionResult",
]
