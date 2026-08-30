"""
Pydantic v2 schemas for the ML detection pipeline.

Defines type-safe data contracts between the ML module and the agent:

  SensorReading:
    - sensor_id       (str)    : which sensor
    - timestamp       (str)    : time of reading
    - pressure_bar    (float)  : water pressure in bar
    - flow_rate_lps   (float)  : water flow rate in L/s
    - temperature_c   (float)  : local ambient temperature in °C

  DetectionResult:
    - sensor_id       (str)
    - timestamp       (str)
    - verdict         (str)    : "normal" | "suspicious"
    - trigger         (str)    : "z_score" | "ml_model" | "boundary" | "combined" | "none"
    - ml_score        (float)  : Isolation Forest anomaly score
    - z_scores        (dict)   : individual Z-scores for each feature
    - details         (str)    : human-readable explanation
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    """Validated incoming sensor telemetry reading."""

    sensor_id: str = Field(..., description="Sensor identifier (e.g. S001)")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the reading")
    pressure_bar: float = Field(..., ge=0.0, description="Pipeline pressure in bar")
    flow_rate_lps: float = Field(..., ge=0.0, description="Flow rate in litres/second")
    temperature_c: float = Field(..., description="Ambient temperature in °C")


class DetectionResult(BaseModel):
    """Structured output from the anomaly detection pipeline."""

    sensor_id: str = Field(..., description="Sensor identifier")
    timestamp: str = Field(..., description="Timestamp of the evaluated reading")
    verdict: Literal["normal", "suspicious"] = Field(
        ..., description="Final classification"
    )
    trigger: Literal["z_score", "ml_model", "boundary", "combined", "none"] = Field(
        ..., description="Which detection layer triggered the flag"
    )
    ml_score: float = Field(
        ..., description="Isolation Forest anomaly score (more negative = more anomalous)"
    )
    z_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Z-scores for pressure and flow rate",
    )
    details: str = Field(
        ..., description="Human-readable explanation of the detection result"
    )
