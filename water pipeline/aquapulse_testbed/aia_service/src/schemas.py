from typing import List, Optional
from pydantic import BaseModel, Field

# Ingestion Schemas
class TelemetryReading(BaseModel):
    timestamp: str
    pressure_psi: float
    flow_rate_lps: float
    ambient_temp_c: float

class TelemetryWindow(BaseModel):
    sensor_cluster_id: str
    network_metadata: Optional[dict] = None
    readings: List[TelemetryReading]

class StreamingBatchInput(BaseModel):
    batch_id: str
    timestamp: str
    telemetry_windows: List[TelemetryWindow]

# Output Schemas
class NetworkStatus(BaseModel):
    camara_reachability_status: str
    camara_congestion_level: str
    api_unavailable: bool

class PhysicalDeviations(BaseModel):
    pressure_drop_pct: float
    flow_surge_pct: float
    pressure_slope: float
    flow_slope: float
    is_stale_pre_outage_data: bool

class CriticalityMetrics(BaseModel):
    criticality_score: int
    proximity_to_reservoir_m: float
    population_served: int
    associated_valve_id: str

class InvestigatedThreat(BaseModel):
    anomaly_id: str
    sensor_cluster_id: str
    segment_id: str
    classification: str
    severity_tier: int
    network_status: NetworkStatus
    physical_deviations: PhysicalDeviations
    criticality_metrics: CriticalityMetrics
    operator_justification: str
    confidence_score: float

class AIABatchOutput(BaseModel):
    batch_id: str
    analysis_timestamp: str
    total_clusters_analyzed: int
    anomalies_detected_count: int
    investigated_threats: List[InvestigatedThreat]
