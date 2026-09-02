"""
Pydantic v2 models for the Anomaly Investigation Agent.

Covers:
  - Section 3: Streaming Batch Input Schema
  - Section 7: Structured Output Payload Schema
  - Internal per-cluster investigation state threaded through the LangGraph graph
"""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from aia.config import IDENTIFIER_SANITIZATION_REGEX

_ID_RE = re.compile(IDENTIFIER_SANITIZATION_REGEX)


def sanitize_identifier(value: str) -> str:
    """
    Ingestion-boundary sanitizer (Section 6: Prompt Injection Guardrail).
    Only alphanumeric characters and hyphens are accepted, 1-64 chars.
    Raises ValueError if the identifier doesn't match -- this is intentional:
    malformed/spoofed identifiers must never reach the LLM prompt template.
    """
    if not _ID_RE.match(value):
        raise ValueError(
            f"Identifier {value!r} failed sanitization "
            f"(must match {IDENTIFIER_SANITIZATION_REGEX!r})"
        )
    return value


class Reading(BaseModel):
    timestamp: datetime
    pressure_psi: float
    flow_rate_lps: float
    ambient_temp_c: float


class NetworkMetadata(BaseModel):
    signal_strength_dbm: Optional[int] = None
    packet_loss_pct: Optional[float] = None


class TelemetryWindow(BaseModel):
    sensor_cluster_id: str
    network_metadata: Optional[NetworkMetadata] = None
    readings: list[Reading] = Field(min_length=1)

    @field_validator("sensor_cluster_id")
    @classmethod
    def _sanitize(cls, v: str) -> str:
        return sanitize_identifier(v)


class StreamingBatch(BaseModel):
    batch_id: str
    timestamp: datetime
    telemetry_windows: list[TelemetryWindow]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Classification(str, Enum):
    CONFIRMED_ANOMALY = "confirmed_anomaly"
    LIKELY_CONNECTIVITY_ARTIFACT = "likely_connectivity_artifact"
    CONFIRMED_INSTRUMENT_FAULT = "confirmed_instrument_fault"
    INSUFFICIENT_DATA = "insufficient_data"


class CongestionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNAVAILABLE = "UNAVAILABLE"


class ReachabilityStatus(str, Enum):
    REACHABLE = "REACHABLE"
    UNREACHABLE = "UNREACHABLE"
    UNKNOWN = "UNKNOWN"  # used only when api_unavailable=True


# ---------------------------------------------------------------------------
# Output models (Section 7)
# ---------------------------------------------------------------------------

class NetworkStatus(BaseModel):
    camara_reachability_status: str
    camara_congestion_level: CongestionLevel
    api_unavailable: bool


class PhysicalDeviations(BaseModel):
    pressure_drop_pct: float
    flow_surge_pct: float
    pressure_slope: float = 0.0
    flow_slope: float = 0.0
    is_stale_pre_outage_data: bool = False


# criticality selon : la proximite au reservoir et aussi le nombre de gens servis
class CriticalityMetrics(BaseModel):
    criticality_score: int = Field(ge=1, le=3)
    proximity_to_reservoir_m: float
    population_served: int
    associated_valve_id: str
    pipe_diameter_mm: float = 200.0

    @field_validator("associated_valve_id")
    @classmethod
    def _sanitize(cls, v: str) -> str:
        return sanitize_identifier(v)


class InvestigatedThreat(BaseModel):
    anomaly_id: str = Field(default_factory=lambda: str(uuid4()))
    sensor_cluster_id: str
    segment_id: str
    classification: Classification
    severity_tier: int = Field(ge=1, le=3)
    network_status: NetworkStatus
    physical_deviations: PhysicalDeviations
    criticality_metrics: CriticalityMetrics
    operator_justification: str
    confidence_score: float = Field(ge=0.0, le=1.0)

    @field_validator("sensor_cluster_id", "segment_id")
    @classmethod
    def _sanitize(cls, v: str) -> str:
        return sanitize_identifier(v)


class AIABatchOutputPayload(BaseModel):
    batch_id: str
    analysis_timestamp: datetime
    total_clusters_analyzed: int
    anomalies_detected_count: int
    investigated_threats: list[InvestigatedThreat] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal per-cluster investigation state (threaded through the LangGraph graph)
# ---------------------------------------------------------------------------

class ClusterInvestigationState(BaseModel):
    """
    Mutable working state for a single suspicious cluster as it flows through
    Stage 2 -> Stage 3 -> Stage 4. Not part of the external contract.
    """
    model_config = {"arbitrary_types_allowed": True}

    anomaly_id: str = Field(default_factory=lambda: str(uuid4()))
    sensor_cluster_id: str
    window: TelemetryWindow

    # Stage 1 outputs
    z_score_pressure: float = 0.0
    z_score_flow: float = 0.0
    ml_confidence: Optional[float] = None
    detection_reason: str = ""

    # Stage 2 outputs
    camara_reachability_status: Optional[ReachabilityStatus] = None
    camara_congestion_level: Optional[CongestionLevel] = None
    api_unavailable: bool = False
    reachability_api_unavailable: bool = False
    congestion_api_unavailable: bool = False
    api_error_detail: Optional[str] = None
    consecutive_insufficient_data_cycles: int = 0
    classification: Optional[Classification] = None

    # Stage 3 outputs
    segment_id: Optional[str] = None
    criticality_score: Optional[int] = None
    proximity_to_reservoir_m: Optional[float] = None
    population_served: Optional[int] = None
    associated_valve_id: Optional[str] = None
    pipe_diameter_mm: Optional[float] = None
    zone_id: Optional[str] = None
    pressure_drop_pct: float = 0.0
    flow_surge_pct: float = 0.0
    pressure_slope: float = 0.0
    flow_slope: float = 0.0
    trend_r_squared: float = 1.0
    is_stale_pre_outage_data: bool = False
    severity_tier: Optional[int] = None
    confidence_score: Optional[float] = None
    estimated_volume_loss_lpm: Optional[float] = None

    # Stage 4 outputs
    operator_justification: Optional[str] = None

    # Retry routing (Stage 2 escalation / requeue)
    requeue: bool = False
    escalate_to_human: bool = False
