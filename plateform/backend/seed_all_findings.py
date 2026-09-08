import json
import urllib.request
from datetime import datetime, timezone

# 1. Fetch detection IDs from backend
req_det = urllib.request.Request("http://127.0.0.1:8000/api/detections")
with urllib.request.urlopen(req_det) as resp:
detections = json.loads(resp.read().decode())

print(f"Found {len(detections)} detections in backend.")

# 2. Build threats array handling both strings and dicts
threats = []
for det in detections:
anomaly_id = det if isinstance(det, str) else det.get("detection_number", det.get("id"))
severity = 1 if isinstance(det, str) else det.get("severity_tier", 1)

threats.append({
    "anomaly_id": anomaly_id,
    "classification": "confirmed_anomaly",
    "severity_tier": severity,
    "confidence_score": 0.92,
    "sensor_cluster_id": "CLUSTER-01",
    "segment_id": "SEG-01",
    "network_status": {
        "reachability": "REACHABLE",
        "latency_ms": 12,
        "camara_reachability_status": "REACHABLE",
        "camara_congestion_level": "LOW",
        "api_unavailable": False
    },
    "physical_deviations": {
        "pressure_drop_psi": 15.5
    },
    "criticality_metrics": {
        "associated_valve_id": "VALVE-01"
    },
    "operator_justification": f"Automated batch investigation result for {anomaly_id}."
})

payload = {
"schema_version": "1.0",
"data_mode": "simulated",
"batch": {
    "batch_id": f"batch-all-{int(datetime.now().timestamp())}",
    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    "total_clusters_analyzed": 1,
    "anomalies_detected_count": len(threats),
    "investigated_threats": threats
}
}

# 3. Post batch to ingestion endpoint
url = "http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results"
req_post = urllib.request.Request(
url,
data=json.dumps(payload).encode("utf-8"),
headers={"Content-Type": "application/json"}
)

try:
with urllib.request.urlopen(req_post) as resp:
    print("SUCCESS:", resp.status, resp.read().decode())
except urllib.error.HTTPError as e:
print("HTTP Error:", e.code, e.read().decode())
