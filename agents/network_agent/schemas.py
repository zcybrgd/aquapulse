from datetime import datetime, timezone
from enum import IntEnum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field


class SeverityTier(IntEnum):
    TIER_1_MONITOR = 1  # log
    TIER_2_ALERT = 2  # alert human operator
    TIER_3_AUTONOMOUS = 3  # autonomous valve isolation + simultaneous human alert


class NetworkStatus(BaseModel):
    device_online: bool
    device_reachable: bool
    network_degradation_detected: bool
    camara_device_status: str
    camara_reachability_status: str


class PhysicalDeviations(BaseModel):
    pressure_drop_pct: float
    flow_surge_pct: float
    pressure_slope: float
    flow_slope: float


class CriticalityMetrics(BaseModel):
    criticality_score: int = Field(..., ge=1, le=5, description="Criticality score from 1 to 5")
    proximity_to_reservoir_m: float
    population_served: int
    associated_valve_id: str


class InvestigatedThreat(BaseModel):
    anomaly_id: str = Field(..., description="Unique anomaly identifier (incident ID)")
    sensor_cluster_id: str = Field(..., description="Sensor cluster ID (cluster ID)")
    segment_id: str = Field(..., description="Pipeline segment identifier")
    device_id: str
    classification: str = Field(..., description="Anomaly classification status")
    severity_tier: int = Field(..., ge=1, le=3, description="Severity tier (1=Routine, 2=Moderate, 3=Critical)")
    network_status: NetworkStatus
    physical_deviations: PhysicalDeviations
    criticality_metrics: CriticalityMetrics
    operator_justification: str
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")


class BatchInput(BaseModel):
    batch_id: str
    analysis_timestamp: str
    total_clusters_analyzed: int
    anomalies_detected_count: int
    investigated_threats: List[InvestigatedThreat]


class RegionalBatch(BaseModel):
    zone_id: str = Field(..., description="Geographic zone or sensor cluster identifier")
    representative_device_id: Optional[str] = Field(None, description="Device ID or phone number used as proxy")
    requests: List[InvestigatedThreat] = Field(default_factory=list)


class NetworkGrant(BaseModel):
    cluster_id: str
    incident_id: str
    severity_tier: Union[SeverityTier, int, str]
    guarantee_type: Literal["QoD", "slice"]
    session_id: str
    granted_at: datetime
    reasoning_trace: str
    expires_at: Optional[datetime] = None


class NetworkDenied(BaseModel):
    cluster_id: str
    incident_id: str
    severity_tier: Union[SeverityTier, int, str]
    reasoning_trace: str
    fallback: Literal["SMS", "none"] = "SMS"
    denied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CongestionCheckResult(BaseModel):
    zone_id: str
    representative_device_id: str
    congestion_level: str
    status: Optional[str] = "SUCCESS"
    error: Optional[str] = None