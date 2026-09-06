from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.integrations.constants import CLASSIFICATION_ANOMALY, CLASSIFICATION_FAULT, CONTRACT_VERSION


class OptionalMetric(BaseModel):
    value: float | None = None
    values: list[float] | None = None
    unit: str | None = None
    available: bool = False


class InvestigationClusterV1(BaseModel):
    """Documented fields sent to the Investigation Agent. Missing values stay null."""

    model_config = ConfigDict(extra="forbid")

    cluster_id: str
    external_aliases: list[str] = Field(default_factory=list)
    segment_id: str | None = None
    sensor_ids: list[str] = Field(default_factory=list)
    telemetry_window: dict[str, datetime]
    pressure: OptionalMetric
    flow: OptionalMetric
    data_freshness: str | None = None
    network_context: dict[str, Any] | None = None
    temperature: OptionalMetric
    criticality: int | None = None
    population_served: int | None = None
    associated_valve_id: str | None = None
    pipe_diameter_mm: float | None = None
    pipe_diameter_available: bool = False
    population_available: bool = False
    data_mode: str = "simulated"


class InvestigationBatchRequestV1(BaseModel):
    batch_id: str
    analysis_timestamp: datetime
    clusters: list[InvestigationClusterV1] = Field(default_factory=list)


class InvestigationRequestV1(BaseModel):
    schema_version: Literal["1.0"] = CONTRACT_VERSION
    run_id: str
    requested_at: datetime
    data_mode: str = "simulated"
    batch: InvestigationBatchRequestV1


class NetworkStatusV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    camara_reachability_status: str
    camara_congestion_level: str
    api_unavailable: bool


class PhysicalDeviationsV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    pressure_drop_pct: float | None = None
    flow_surge_pct: float | None = None
    pressure_slope: float | None = None
    flow_slope: float | None = None
    is_stale_pre_outage_data: bool | None = None


class CriticalityMetricsV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    criticality_score: int | None = None
    proximity_to_reservoir_m: float | None = None
    population_served: int | None = None
    associated_valve_id: str | None = None
    pipe_diameter_mm: float | None = None


class InvestigatedThreatV1(BaseModel):
    """Friend Investigation Agent finding. `confirmed_*` is an agent assessment, not human confirmation."""

    model_config = ConfigDict(extra="allow")

    anomaly_id: str
    sensor_cluster_id: str
    segment_id: str
    classification: Literal["confirmed_anomaly", "confirmed_instrument_fault"]
    severity_tier: int
    network_status: NetworkStatusV1
    physical_deviations: PhysicalDeviationsV1
    criticality_metrics: CriticalityMetricsV1
    operator_justification: str
    confidence_score: float
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity_tier")
    @classmethod
    def severity_range(cls, value: int) -> int:
        if value not in (1, 2, 3):
            raise ValueError("severity_tier must be 1, 2 or 3")
        return value

    @field_validator("confidence_score")
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence_score must be between 0 and 1")
        return value

    @field_validator("classification")
    @classmethod
    def classification_allowed(cls, value: str) -> str:
        if value not in (CLASSIFICATION_ANOMALY, CLASSIFICATION_FAULT):
            raise ValueError("unsupported classification")
        return value

    @model_validator(mode="before")
    @classmethod
    def capture_extensions(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        known = set(cls.model_fields)
        extras = {key: value for key, value in data.items() if key not in known and key != "extensions"}
        if extras:
            merged = dict(data)
            existing = dict(merged.get("extensions") or {})
            existing.update(extras)
            for key in extras:
                merged.pop(key, None)
            merged["extensions"] = existing
            return merged
        return data


class InvestigationBatchResultV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    batch_id: str
    analysis_timestamp: datetime
    total_clusters_analyzed: int
    anomalies_detected_count: int
    investigated_threats: list[InvestigatedThreatV1]

    @model_validator(mode="after")
    def counts_match(self) -> InvestigationBatchResultV1:
        findings = len(self.investigated_threats)
        if self.anomalies_detected_count != findings:
            raise ValueError("anomalies_detected_count does not match investigated_threats")
        if self.total_clusters_analyzed < 0:
            raise ValueError("total_clusters_analyzed must be >= 0")
        cluster_ids = {item.sensor_cluster_id for item in self.investigated_threats}
        if self.investigated_threats and self.total_clusters_analyzed < len(cluster_ids):
            raise ValueError("total_clusters_analyzed is lower than distinct clusters in findings")
        return self


class InvestigationResponseV1(BaseModel):
    schema_version: Literal["1.0"] = CONTRACT_VERSION
    run_id: str | None = None
    data_mode: str = "simulated"
    batch: InvestigationBatchResultV1
    extensions: dict[str, Any] = Field(default_factory=dict)


class AgentHealth(BaseModel):
    agent_code: str
    status: Literal["disabled", "healthy", "unhealthy", "unreachable", "unknown"]
    contract_version: str = CONTRACT_VERSION
    reachable: bool = False
    checked_at: datetime | None = None
    detail: str | None = None
    data_mode: str = "mock"
