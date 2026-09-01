import os
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from src.schemas import StreamingBatchInput, AIABatchOutput, InvestigatedThreat, NetworkStatus, PhysicalDeviations, CriticalityMetrics
from src.detection import AnomalyDetector
from src.risk_assessment import RiskAssessor
from src.investigation import CAMARADiagnosticClient
from src.narration import LLMNarrator

app = FastAPI(title="AquaPulse Anomaly Investigation Agent (AIA) API Service")

# Initialize modules
detector = AnomalyDetector(model_path="data/isolation_forest_bootstrap.joblib")
assessor = RiskAssessor(topology_path="config/topology_cache.json")
camara_client = CAMARADiagnosticClient()
narrator = LLMNarrator()

@app.post("/ingest", response_model=AIABatchOutput)
def ingest_telemetry_batch(batch: StreamingBatchInput):
    """
    Ingest trailing telemetry windows, execute detection, run API diagnostics,
    perform risk assessment, and compile structured threat payload for the NMA.
    """
    investigated_threats = []
    
    for window in batch.telemetry_windows:
        cluster_id = window.sensor_cluster_id
        
        # Stage 1: Continuous Ingestion & Filtering (Anomaly Detection)
        is_suspicious = detector.evaluate_sequence(window.readings)
        
        if is_suspicious:
            # Stage 2: Active Investigation
            reach_data = camara_client.query_reachability(cluster_id)
            cong_data = camara_client.query_congestion(cluster_id)
            
            reach_status = reach_data["reachability_status"]
            cong_level = cong_data["congestion_level"]
            api_unavail = reach_data["api_unavailable"] or cong_data["api_unavailable"]
            
            # Stage 3: Deterministic Risk Assessment & Severity
            diag = assessor.assess(
                sensor_cluster_id=cluster_id,
                readings=window.readings,
                reachability=reach_status,
                congestion=cong_level,
                api_unavailable=api_unavail
            )
            
            # Stage 4: AI Narration & Memo compilation
            memo = narrator.generate_memo(
                cluster_id=cluster_id,
                diagnostics=diag,
                reach_status=reach_status,
                cong_level=cong_level
            )
            
            # Compile sub-objects
            net_status = NetworkStatus(
                camara_reachability_status=reach_status,
                camara_congestion_level=cong_level,
                api_unavailable=api_unavail
            )
            
            phys_dev = PhysicalDeviations(
                pressure_drop_pct=diag["physical_deviations"]["pressure_drop_pct"],
                flow_surge_pct=diag["physical_deviations"]["flow_surge_pct"],
                pressure_slope=diag["physical_deviations"]["pressure_slope"],
                flow_slope=diag["physical_deviations"]["flow_slope"],
                is_stale_pre_outage_data=diag["physical_deviations"]["is_stale_pre_outage_data"]
            )
            
            crit_met = CriticalityMetrics(
                criticality_score=diag["criticality_metrics"]["criticality_score"],
                proximity_to_reservoir_m=diag["criticality_metrics"]["proximity_to_reservoir_m"],
                population_served=diag["criticality_metrics"]["population_served"],
                associated_valve_id=diag["criticality_metrics"]["associated_valve_id"]
            )
            
            threat = InvestigatedThreat(
                anomaly_id=f"anom-{cluster_id}-{int(datetime.utcnow().timestamp())}",
                sensor_cluster_id=cluster_id,
                segment_id=diag["segment_id"],
                classification=diag["classification"],
                severity_tier=diag["severity_tier"],
                network_status=net_status,
                physical_deviations=phys_dev,
                criticality_metrics=crit_met,
                operator_justification=memo,
                confidence_score=diag["confidence_score"]
            )
            
            investigated_threats.append(threat)
            
            # Immediate Closed-Loop Autonomous Response Hand-Off (Inter-agent handshake)
            # If Tier 3, trigger simulated valve isolation directly for the SCADA demo!
            if diag["classification"] == "confirmed_anomaly" and diag["severity_tier"] == 3:
                valve_url = f"{camara_client.simulator_url}/control-valve"
                try:
                    requests.post(valve_url, json={
                        "valve_id": diag["criticality_metrics"]["associated_valve_id"],
                        "state": "CLOSED"
                    }, timeout=2.0)
                    print(f"[AIA - main] Autonomous closed-loop valve shutdown triggered for {diag['criticality_metrics']['associated_valve_id']}")
                except Exception as e:
                    print(f"[AIA - main] Failed to issue autonomous valve isolation command: {e}")

    return AIABatchOutput(
        batch_id=batch.batch_id,
        analysis_timestamp=datetime.utcnow().isoformat() + "Z",
        total_clusters_analyzed=len(batch.telemetry_windows),
        anomalies_detected_count=len(investigated_threats),
        investigated_threats=investigated_threats
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
