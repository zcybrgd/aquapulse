# Response Agent field mapping

| Agent field | AquaPulse treatment |
| --- | --- |
| `incident_id` | Stored as external ID; attached only when mapped |
| `cluster_id` | Stored; mapped only when configured |
| `device_id` | Stored; mapped only when configured |
| `severity_tier` | 1 monitor / 2 alert / 3 critical recommendation |
| `decision` | Advisory enum |
| `notification_sent` | Recorded as reported; AquaPulse keeps `sent: false` |
| `valve_command_sent` / `confirmed` | Labelled `agent_reported_unverified` |
| `human_override_requested` | Not treated as approval |
| `network_grant` | Never authorization to actuate |
| `reasoning_trace` | Stored; never authorization |

Unknown non-dangerous fields go to `extensions`. Malformed safety-critical fields are rejected.
