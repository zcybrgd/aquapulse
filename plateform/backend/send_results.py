import json
import urllib.request
from datetime import datetime, timezone

payload = {
    "schema_version": "1.0",
    "data_mode": "simulated",
    "batch": {
        "batch_id": "batch-test-001",
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_clusters_analyzed": 1,
        "anomalies_detected_count": 1,
        "investigated_threats": [
            {
                "anomaly_id": "DET-001",
                "classification": "confirmed_anomaly",
                "severity_tier": 1,
                "confidence_score": 0.94,
                "sensor_cluster_id": "CLUSTER-01",
                "segment_id": "SEG-01",
                "network_status": {
                    "reachability": "REACHABLE",
                    "latency_ms": 15,
                    "camara_reachability_status": "REACHABLE",
                    "camara_congestion_level": "LOW",
                    "api_unavailable": False
                },
                "physical_deviations": {
                    "pressure_drop_psi": 18.2
                },
                "criticality_metrics": {
                    "associated_valve_id": "VALVE-01"
                },
                "operator_justification": "Significant pressure loss detected downstream of Pipe Segment P-1."
            }
        ]
    }
}

url = "http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results"
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as resp:
        print("SUCCESS:", resp.status, resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode())
except Exception as e:
    print("Error:", e)
