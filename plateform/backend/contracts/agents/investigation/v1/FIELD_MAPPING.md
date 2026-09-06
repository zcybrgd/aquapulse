# Investigation Agent field mapping

| Agent / request field | AquaPulse source | Notes |
| --- | --- | --- |
| `schema_version` | Contract constant `1.0` | Required on the request envelope |
| `run_id` | `AGRUN-000001` | AquaPulse public run ID |
| `batch.batch_id` | `AP-BATCH-…` | Idempotency key |
| `cluster_id` | `AP-CLUSTER-{DET-…}` | Never invented from NEOM demo IDs |
| `external_aliases` | Mapping table | Empty unless configured |
| `segment_id` | Pipeline `external_id` | Example `HBR-XFER-7` |
| `sensor_ids` | Asset `external_id` | Example `SNS-HBR-007` |
| `pressure` / `flow` / `temperature` | Structured evidence | `available: false` and `null` when missing |
| `population_served` | Detection input | `null` when unknown |
| `pipe_diameter_mm` | Not invented | `null` + `pipe_diameter_available: false` |
| `anomaly_id` | Agent result | Unique per provider |
| `sensor_cluster_id` | Agent result | Mapped only when configured |
| `classification` | Agent result | Displayed as agent-assessed labels |

AquaPulse never guesses a mapping from `cluster-desert-042` onto an unrelated asset.
