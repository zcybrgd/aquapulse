# Investigation Agent contract 1.0

AquaPulse sends a versioned request envelope and stores your batch result as advisory evidence.

## Endpoints AquaPulse calls

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Bounded liveness |
| GET | `/v1/contract` | Advertise `schema_version: "1.0"` |
| POST | `/v1/investigate` | Analyze one batch |

If your service uses another POST path, set `INVESTIGATION_AGENT_INVESTIGATE_PATH`.

## Classification display

| Contract value | AquaPulse label |
| --- | --- |
| `confirmed_anomaly` | Agent-assessed anomaly |
| `confirmed_instrument_fault` | Agent-assessed instrument fault |

`confirmed` is not human confirmation and does not create an incident.

## Required finding fields

`anomaly_id`, `sensor_cluster_id`, `segment_id`, `classification`, `severity_tier` (1–3), `network_status`, `physical_deviations`, `criticality_metrics`, `operator_justification`, `confidence_score` (0–1).

`anomalies_detected_count` must equal `investigated_threats.length`.

Unknown fields that are not safety-critical are stored in `extensions`.
