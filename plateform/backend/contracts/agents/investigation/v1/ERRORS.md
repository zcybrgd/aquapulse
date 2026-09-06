# Investigation Agent error codes

| Code | Meaning |
| --- | --- |
| `agent_execution_disabled` | Remote execution is off (default) |
| `agent_not_configured` | Mode is remote but no trusted URL is set |
| `agent_unreachable` | Transport or 5xx failure |
| `agent_timeout` | Deadline exceeded |
| `agent_contract_mismatch` | Payload failed contract 1.0 |
| `agent_invalid_response` | Malformed JSON or invalid values |
| `agent_schema_version_unsupported` | `schema_version` is not `1.0` |
| `agent_result_duplicate` | `anomaly_id` or batch already stored |
| `agent_identity_unmapped` | External ID has no mapping |
| `agent_result_rejected` | Result rejected; transaction rolled back |
