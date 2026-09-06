# AquaPulse Agent Integration

This document tells the Investigation Agent and Response Agent teams exactly what AquaPulse expects to receive.

Agent orchestration is managed **outside** AquaPulse. AquaPulse does not start, schedule or implement those agents. It receives their **final outputs**, then validates, maps, stores, sanitizes and displays them.

AquaPulse does not invent agent decisions. Screening priority from the lightweight detection model is not final severity.

**Network Agent integration is outside the scope of this document.**

Authoritative runtime sources:

| Item | Location |
| --- | --- |
| Investigation Pydantic models | `plateform/backend/app/integrations/contracts/investigation.py` |
| Response Pydantic models | `plateform/backend/app/integrations/contracts/response.py` |
| Parsers | `plateform/backend/app/integrations/adapters/investigation.py`, `.../response.py` |
| JSON Schema | `plateform/backend/contracts/agents/investigation/v1/response.schema.json`, `.../response/v1/response.schema.json` |
| HTTP routes | `plateform/backend/app/api/routes/integrations.py` |
| Persistence | `agent_runs`, `agent_findings`, `agent_response_recommendations` |
| Structured errors | `{"detail": {"message": "...", "code": "..."}}` |

Contract version: **`1.0`**.

---

## Incoming HTTP ingest status

The intended AquaPulse ingest paths are:

```text
POST /api/integrations/agents/investigation/v1/results
POST /api/integrations/agents/response/v1/results
```

Development URLs:

```text
http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results
http://127.0.0.1:8000/api/integrations/agents/response/v1/results
```

**Both paths are required endpoints — not implemented yet.** They are not registered in FastAPI. Do not treat them as active.

What exists today:

| Capability | Status | Path / entry point |
| --- | --- | --- |
| Validate Investigation output (no persist) | Implemented | `POST /api/integrations/agents/contracts/investigation/v1/validate-response` |
| Validate Response output (no persist) | Implemented | `POST /api/integrations/agents/contracts/response/v1/validate-response` |
| Persist Investigation output | Service only, no HTTP | `IntegrationService.ingest_investigation_result` |
| Persist Response output | Service only, no HTTP | `IntegrationService.ingest_response_result` |
| List stored findings | Implemented | `GET /api/integrations/agents/findings` |
| List stored recommendations | Implemented | `GET /api/integrations/agents/recommendations` |
| List / get runs | Implemented | `GET /api/integrations/agents/runs`, `GET /api/integrations/agents/runs/{run_id}` |
| Agent Audit Trail | Implemented | `GET /api/agent-audit/...` |
| Remote agent execution | Disabled | `POST /api/integrations/agents/{agent_code}/execute` always returns `503` |

`AGENT_RESULT_INGEST_ENABLED` defaults to `false` and is reported on `/api/integrations/agents/readiness`. The Python ingest methods do **not** currently reject a payload because that flag is false. There is still no public HTTP ingest route to enable.

---

## Main integration table

| Agent | Data | Expected format | Required | Endpoint | Displayed/used in AquaPulse |
| --- | --- | --- | --- | --- | --- |
| Investigation | `schema_version` | string, const `1.0` | Optional on the raw batch; default `1.0` on the wrapper | `POST /api/integrations/agents/investigation/v1/results` — **not implemented yet**. Validate today: `POST /api/integrations/agents/contracts/investigation/v1/validate-response` | Stored on `agent_runs.contract_version` |
| Investigation | `run_id` | string or null | Optional | Same | `agent_runs.public_id` is assigned by AquaPulse (`AGRUN-…`) |
| Investigation | `data_mode` | string | Optional, default `simulated` | Same | `agent_runs.data_mode` |
| Investigation | `batch` | object (`InvestigationBatchResultV1`) | Required if using the wrapper envelope | Same | Unwrapped and persisted as findings |
| Investigation | `batch_id` | string | Required | Same | Idempotency default `investigation:{batch_id}`; `agent_runs.source_public_id` |
| Investigation | `analysis_timestamp` | ISO-8601 date-time | Required | Same | Stored in sanitized `agent_runs.response_payload` |
| Investigation | `total_clusters_analyzed` | integer ≥ 0, and ≥ distinct `sensor_cluster_id` values | Required | Same | Stored in `response_payload` |
| Investigation | `anomalies_detected_count` | integer, must equal `investigated_threats.length` | Required | Same | Stored in `response_payload` |
| Investigation | `investigated_threats` | array of objects | Required | Same | One `agent_findings` row per item |
| Investigation | `investigated_threats[].anomaly_id` | string | Required | Same | `agent_findings.external_anomaly_id` (unique per provider). Duplicate → `409 agent_result_duplicate` |
| Investigation | `investigated_threats[].sensor_cluster_id` | string | Required | Same | `agent_findings.external_cluster_id`; mapped only if configured |
| Investigation | `investigated_threats[].segment_id` | string | Required | Same | `agent_findings.external_segment_id` |
| Investigation | `investigated_threats[].classification` | enum string | Required | Same | `agent_findings.classification`; Investigation Queue / Detection Details / Agent Audit |
| Investigation | `investigated_threats[].severity_tier` | integer `1`, `2` or `3` | Required | Same | `agent_findings.severity_tier`; Detection Details; Agent Audit |
| Investigation | `investigated_threats[].network_status` | object | Required | Same | `agent_findings.network_status` JSON |
| Investigation | `network_status.camara_reachability_status` | string | Required | Same | Stored; not used as CAMARA execution authority |
| Investigation | `network_status.camara_congestion_level` | string | Required | Same | Stored |
| Investigation | `network_status.api_unavailable` | boolean | Required | Same | Stored |
| Investigation | `investigated_threats[].physical_deviations` | object | Required (inner metrics nullable) | Same | `agent_findings.physical_deviations` |
| Investigation | `physical_deviations.pressure_drop_pct` | number or null | Optional, default null | Same | Stored |
| Investigation | `physical_deviations.flow_surge_pct` | number or null | Optional, default null | Same | Stored |
| Investigation | `physical_deviations.pressure_slope` | number or null | Optional, default null | Same | Stored |
| Investigation | `physical_deviations.flow_slope` | number or null | Optional, default null | Same | Stored |
| Investigation | `physical_deviations.is_stale_pre_outage_data` | boolean or null | Optional, default null | Same | Stored |
| Investigation | `investigated_threats[].criticality_metrics` | object | Required (inner metrics nullable) | Same | `agent_findings.criticality_metrics` |
| Investigation | `criticality_metrics.criticality_score` | integer or null | Optional, default null | Same | Stored |
| Investigation | `criticality_metrics.proximity_to_reservoir_m` | number or null | Optional, default null | Same | Stored |
| Investigation | `criticality_metrics.population_served` | integer or null | Optional, default null | Same | Stored |
| Investigation | `criticality_metrics.associated_valve_id` | string or null | Optional, default null | Same | `agent_findings.external_valve_id`; mapped only if configured |
| Investigation | `criticality_metrics.pipe_diameter_mm` | number or null | Optional, default null | Same | Stored |
| Investigation | `investigated_threats[].operator_justification` | string | Required | Same | Detection Details; Agent Audit; Integration finding page |
| Investigation | `investigated_threats[].confidence_score` | number, `0`–`1` inclusive | Required | Same | Detection Details; Agent Audit. **Not leak probability** unless the agent team confirms calibration |
| Investigation | `investigated_threats[].extensions` | object | Optional | Same | Unknown extra keys are captured here |
| Response | `schema_version` | string, const `1.0` | Optional, default `1.0` | `POST /api/integrations/agents/response/v1/results` — **not implemented yet**. Validate today: `POST /api/integrations/agents/contracts/response/v1/validate-response` | `agent_runs.contract_version` |
| Response | `result_id` | string | Required | Same | `agent_response_recommendations.external_result_id`; idempotency default `response:{result_id}` |
| Response | `incident_id` | string | Required | Same | `external_incident_id`; attached to an incident only when mapped |
| Response | `cluster_id` | string | Required | Same | `external_cluster_id` |
| Response | `device_id` | string | Required | Same | `external_device_id`; mapped as device or valve |
| Response | `severity_tier` | integer `1`, `2` or `3` | Required | Same | Stored; Agent Audit; Integration recommendation page |
| Response | `reachability` | object | Optional, default `{}` | Same | `agent_response_recommendations.reachability` |
| Response | `reachability.status` | string (fixture convention) | Not schema-required | Same | Stored if supplied |
| Response | `reachability.device_id` | string | Not schema-required | Same | Stored if supplied |
| Response | `reachability.reachable` | boolean | Not schema-required | Same | Stored if supplied |
| Response | `reachability.checked_at` | ISO-8601 date-time | Not schema-required | Same | Stored if supplied |
| Response | `reachability.raw_signal_quality` | string or number | Not schema-required | Same | Stored if supplied. Compat API uses integer; the Response contract does not constrain the type |
| Response | `decision` | enum string | Required | Same | `agent_response_recommendations.decision`; Agent Audit; Integrations |
| Response | `notification_sent` | boolean | Optional, default `false` | Same | Agent-reported only. AquaPulse stores the recommendation with `notification_sent=false` and `notification_verified=false` |
| Response | `valve_command_sent` | boolean | Optional, default `false` | Same | Stored as reported; `valve_command_verified` stays `false` |
| Response | `valve_command_confirmed` | boolean | Optional, default `false` | Same | Stored as reported; unverified |
| Response | `human_override_requested` | boolean | Optional, default `false` | Same | Stored. **Not** treated as human approval |
| Response | `human_override_response` | string or null | Optional, default null | Same | Stored. **Not** treated as approval |
| Response | `reasoning_trace` | array or object | Optional, default `[]` | Same | Agent Audit (unverified agent-provided reasoning) |
| Response | `created_at` | ISO-8601 date-time | Required | Same | Stored in payload; run timestamps are AquaPulse wall clock |
| Response | `audit` | object or null | Optional | Same | Stored in sanitized `response_payload` |
| Response | `audit.entry_id` | string | Required if `audit` is present | Same | Stored |
| Response | `audit.incident_id` | string | Required if `audit` is present | Same | Stored |
| Response | `audit.cluster_id` | string | Required if `audit` is present | Same | Stored |
| Response | `audit.severity_tier` | integer | Required if `audit` is present | Same | Stored |
| Response | `audit.network_grant` | object or null | Optional | Same | Stored. Never authorization to actuate |
| Response | `audit.network_grant.granted` | boolean | Optional on `NetworkGrantV1`, default `false` | Same | Stored |
| Response | `audit.network_grant.expires_at` | date-time or null | Optional | Same | Required on **request** grants when `granted` is true; optional on result audit |
| Response | `audit.network_grant.grant_id` | string or null | Optional | Same | Stored |
| Response | `audit.network_grant.data_mode` | string | Optional, default `mock` | Same | Stored |
| Response | `audit.network_denied` | object or null | Optional | Same | Stored |
| Response | `audit.network_denied.denied` | boolean | Optional on `NetworkDeniedV1`, default `true` | Same | Stored |
| Response | `audit.network_denied.reason` | string or null | Optional | Same | Stored |
| Response | `audit.network_denied.data_mode` | string | Optional, default `mock` | Same | Stored |
| Response | `audit.actuation_result` | **string or null** | Optional | Same | Stored as text. A nested actuation object is **not** valid here |
| Response | `audit.logged_at` | ISO-8601 date-time | Required if `audit` is present | Same | Stored |
| Response | `extensions` | object | Optional | Same | Unknown non-safety fields |
| Response | `audit_entry` (alternate envelope) | object | **Not in current schema** | Same | Rejected as the top-level result. Use `audit` on `ResponseResultV1` |
| Response | `operator_message` | string | **Not in current schema** | Same | Not persisted as a first-class field |
| Response | `error` | string or null | **Not in current schema** | Same | Not part of a successful result contract |

---

## Investigation Agent endpoint

```text
POST /api/integrations/agents/investigation/v1/results
```

Development URL:

```text
http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results
```

```text
Required endpoint — not implemented yet
```

Use the validation route until ingest HTTP exists:

```text
POST /api/integrations/agents/contracts/investigation/v1/validate-response
http://127.0.0.1:8000/api/integrations/agents/contracts/investigation/v1/validate-response
```

### Accepted payload shapes

`parse_investigation_response` accepts **either**:

1. The friend-team raw batch (top-level `batch_id`, no `batch` wrapper). This is the format AquaPulse fixtures use.
2. The AquaPulse wrapper `{ "schema_version": "1.0", "run_id": "...", "data_mode": "simulated", "batch": { ... } }`.

Unknown extra keys on a threat that are not already model fields are moved into `extensions`.

### Expected raw payload

```json
{
  "batch_id": "batch-2026-08-31-001",
  "analysis_timestamp": "2026-08-31T02:00:00Z",
  "total_clusters_analyzed": 3,
  "anomalies_detected_count": 3,
  "investigated_threats": [
    {
      "anomaly_id": "e048d424-6a15-47ed-a35c-b3cc4c5ff445",
      "sensor_cluster_id": "cluster-desert-042",
      "segment_id": "seg-neom-north-01",
      "classification": "confirmed_anomaly",
      "severity_tier": 3,
      "network_status": {
        "camara_reachability_status": "REACHABLE",
        "camara_congestion_level": "LOW",
        "api_unavailable": false
      },
      "physical_deviations": {
        "pressure_drop_pct": 36.607142857142854,
        "flow_surge_pct": 40.274314214463836,
        "pressure_slope": -1.9033333333333344,
        "flow_slope": 3.9316666666666653,
        "is_stale_pre_outage_data": false
      },
      "criticality_metrics": {
        "criticality_score": 3,
        "proximity_to_reservoir_m": 120.0,
        "population_served": 45000,
        "associated_valve_id": "valve-neom-north-01",
        "pipe_diameter_mm": 400.0
      },
      "operator_justification": "Agent-generated justification.",
      "confidence_score": 0.9078
    }
  ]
}
```

The example above is valid for **one** threat only if `total_clusters_analyzed` and `anomalies_detected_count` are both `1`. For three threats, those counts must be `3` and the array must contain three items. See the complete three-threat fixture in `plateform/backend/app/integrations/fixtures.py` (`INVESTIGATION_EXAMPLE_BATCH`).

### Investigation Agent field table

| JSON path | Description | Type/format | Required | Allowed values/range | Example | AquaPulse destination |
| --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | Contract version on the wrapper | string | Optional | `1.0` only. Other values → `agent_schema_version_unsupported` | `"1.0"` | `agent_runs.contract_version` |
| `run_id` | Optional agent-side run id | string or null | Optional | Any string | `"AGRUN-000206"` | Not used as AquaPulse public id |
| `data_mode` | Provenance label | string | Optional | Default `simulated` | `"simulated"` | `agent_runs.data_mode` |
| `batch` | Wrapper around the friend batch | object | Required when the payload is wrapped | `InvestigationBatchResultV1` | see below | Unwrapped into findings |
| `batch_id` | Batch identity | string | Required | Non-empty string | `"batch-2026-08-31-001"` | Default idempotency `investigation:{batch_id}` |
| `analysis_timestamp` | When the agent finished analysis | date-time (ISO-8601, timezone aware preferred) | Required | Valid datetime | `"2026-08-31T02:00:00Z"` | `response_payload` |
| `total_clusters_analyzed` | Clusters examined | integer | Required | `>= 0` and `>=` distinct `sensor_cluster_id` values | `3` | `response_payload` |
| `anomalies_detected_count` | Finding count | integer | Required | Must equal `investigated_threats.length` | `3` | `response_payload` |
| `investigated_threats` | Findings | array | Required | Zero or more `InvestigatedThreatV1` | `[{...}]` | `agent_findings` |
| `investigated_threats[].anomaly_id` | Agent finding id | string | Required | Unique per `investigation_agent` | `"e048d424-6a15-47ed-a35c-b3cc4c5ff445"` | `agent_findings.external_anomaly_id` |
| `investigated_threats[].sensor_cluster_id` | External cluster | string | Required | Any string; mapped only if configured | `"cluster-desert-042"` | `external_cluster_id`; Agent Audit |
| `investigated_threats[].segment_id` | External segment | string | Required | Any string | `"seg-neom-north-01"` | `external_segment_id` |
| `investigated_threats[].classification` | Agent assessment | string enum | Required | `confirmed_anomaly`, `confirmed_instrument_fault` | `"confirmed_anomaly"` | Finding + Detection Details |
| `investigated_threats[].severity_tier` | Agent severity | integer | Required | `1`, `2`, `3` | `3` | Finding + Detection Details + Agent Audit |
| `investigated_threats[].network_status` | CAMARA snapshot reported by the agent | object | Required | See child rows | `{...}` | `agent_findings.network_status` |
| `network_status.camara_reachability_status` | Reported reachability | string | Required | No enum in schema. Fixtures: `REACHABLE`, `UNREACHABLE`, `UNKNOWN` | `"REACHABLE"` | Stored JSON |
| `network_status.camara_congestion_level` | Reported congestion | string | Required | No enum in schema. Fixtures: `LOW`, `HIGH` | `"LOW"` | Stored JSON |
| `network_status.api_unavailable` | CAMARA API missing | boolean | Required | `true` / `false` | `false` | Stored JSON |
| `investigated_threats[].physical_deviations` | Physical pattern metrics | object | Required | Child fields nullable | `{...}` | `agent_findings.physical_deviations` |
| `physical_deviations.pressure_drop_pct` | Pressure drop percent | number or null | Optional | Any number or null | `36.607142857142854` | Stored JSON |
| `physical_deviations.flow_surge_pct` | Flow surge percent | number or null | Optional | Any number or null | `40.274314214463836` | Stored JSON |
| `physical_deviations.pressure_slope` | Pressure slope | number or null | Optional | Any number or null | `-1.9033333333333344` | Stored JSON |
| `physical_deviations.flow_slope` | Flow slope | number or null | Optional | Any number or null | `3.9316666666666653` | Stored JSON |
| `physical_deviations.is_stale_pre_outage_data` | Stale / pre-outage flag | boolean or null | Optional | `true` / `false` / null | `false` | Stored JSON |
| `investigated_threats[].criticality_metrics` | Asset criticality reported by the agent | object | Required | Child fields nullable | `{...}` | `agent_findings.criticality_metrics` |
| `criticality_metrics.criticality_score` | Agent criticality | integer or null | Optional | Any integer or null | `3` | Stored JSON |
| `criticality_metrics.proximity_to_reservoir_m` | Distance to reservoir | number or null | Optional | Any number or null | `120.0` | Stored JSON |
| `criticality_metrics.population_served` | Population | integer or null | Optional | Any integer or null | `45000` | Stored JSON |
| `criticality_metrics.associated_valve_id` | External valve | string or null | Optional | Any string or null | `"valve-neom-north-01"` | `external_valve_id` |
| `criticality_metrics.pipe_diameter_mm` | Pipe diameter | number or null | Optional | Any number or null | `400.0` | Stored JSON |
| `investigated_threats[].operator_justification` | Agent-written justification | string | Required | Any string | `"Agent-generated justification."` | Detection Details; Agent Audit; `/integrations/findings/{id}` |
| `investigated_threats[].confidence_score` | Agent confidence | number | Required | `0` inclusive to `1` inclusive | `0.9078` | Detection Details; Agent Audit |
| `investigated_threats[].extensions` | Non-contract extras | object | Optional | Any object | `{}` | Stored in raw finding |

Classifications:

```text
confirmed_anomaly
confirmed_instrument_fault
```

AquaPulse display labels: **Agent-assessed anomaly** and **Agent-assessed instrument fault**. `confirmed_*` is an agent assessment, not human confirmation, and does not create an incident.

Severity values:

```text
1
2
3
```

| Value | Agent-team label | AquaPulse stored label |
| ---: | --- | --- |
| `1` | `TIER_1_MONITOR` | Tier 1 / monitor |
| `2` | `TIER_2_ALERT` | Tier 2 / alert and human review |
| `3` | `TIER_3_AUTONOMOUS` | Tier 3 / critical recommendation requiring platform safety policy |

`confidence_score` must be between `0` and `1`. AquaPulse does **not** treat it as leak probability unless the Investigation Agent team confirms that the score is calibrated as a probability.

Investigation Agent results appear in:

* Investigation Queue (`/detections`) — badge `Agent-assessed` when a **mapped** finding exists
* Detection Details (`/detections/:detectionId`) — classification, severity, confidence, justification
* Integration Readiness (`/integrations`) and finding detail (`/integrations/findings/:id`)
* Agent Audit Trail (`/agent-audit`, `/agent-audit/runs/:runId`)

Unmapped findings remain visible in Agent Audit and Integrations. They do not attach to a detection until an identity mapping exists.

---

## Response Agent endpoint

```text
POST /api/integrations/agents/response/v1/results
```

Development URL:

```text
http://127.0.0.1:8000/api/integrations/agents/response/v1/results
```

```text
Required endpoint — not implemented yet
```

Use the validation route until ingest HTTP exists:

```text
POST /api/integrations/agents/contracts/response/v1/validate-response
http://127.0.0.1:8000/api/integrations/agents/contracts/response/v1/validate-response
```

The Response Agent graph, stored exactly as reported when present in `reasoning_trace`:

```text
reachability_check → llm_response_planner → execute_response → human_override → audit_writer
```

AquaPulse does not rewrite this graph. A separate platform safety result may block `AUTONOMOUS_ISOLATE`. Agent-reported valve or notification results stay unverified.

### Runtime schema versus provided envelope

The current Pydantic model is **`ResponseResultV1`**: a flat recommendation object. `parse_response_result` calls `ResponseResultV1.model_validate(payload)` and does **not** unwrap `{ audit_entry, operator_message, error }`.

The provided envelope below is the format the Response Agent team described. It is documented so the teams can align. **It is not accepted by the current runtime parser** as a top-level body.

```json
{
  "audit_entry": {
    "entry_id": "response-audit-001",
    "incident_id": "INC-1835",
    "cluster_id": "cluster-desert-042",
    "severity_tier": 3,
    "network_grant": null,
    "network_denied": null,
    "actuation_result": {
      "result_id": "response-result-001",
      "incident_id": "INC-1835",
      "cluster_id": "cluster-desert-042",
      "device_id": "valve-neom-north-01",
      "severity_tier": 3,
      "reachability": {
        "device_id": "valve-neom-north-01",
        "reachable": true,
        "checked_at": "2026-08-31T02:01:00Z",
        "raw_signal_quality": "GOOD"
      },
      "decision": "AUTONOMOUS_ISOLATE",
      "notification_sent": false,
      "valve_command_sent": false,
      "valve_command_confirmed": false,
      "human_override_requested": true,
      "human_override_response": null,
      "reasoning_trace": [
        "Device reachable",
        "Tier 3 response recommended"
      ],
      "created_at": "2026-08-31T02:02:00Z"
    },
    "logged_at": "2026-08-31T02:02:01Z"
  },
  "operator_message": "Critical anomaly requires operator attention.",
  "error": null
}
```

Mismatches with `ResponseResultV1`:

| Provided field | Current runtime |
| --- | --- |
| Top-level `audit_entry` | Field name is `audit`, and it is optional on the result |
| Nested `audit_entry.actuation_result` object | `audit.actuation_result` is `string \| null` (fixture value: `"not_executed"`) |
| Top-level `operator_message` | Not a schema field |
| Top-level `error` | Not a schema field for a valid result |
| Decision / ids / reachability inside `actuation_result` | Those fields are **top-level** on `ResponseResultV1` |

Send the flat `ResponseResultV1` object until AquaPulse adds an adapter for the envelope.

### Valid runtime payload

```json
{
  "schema_version": "1.0",
  "result_id": "response-result-001",
  "incident_id": "INC-1835",
  "cluster_id": "cluster-desert-042",
  "device_id": "valve-neom-north-01",
  "severity_tier": 3,
  "reachability": {
    "device_id": "valve-neom-north-01",
    "reachable": true,
    "checked_at": "2026-08-31T02:01:00Z",
    "raw_signal_quality": "GOOD"
  },
  "decision": "AUTONOMOUS_ISOLATE",
  "notification_sent": false,
  "valve_command_sent": false,
  "valve_command_confirmed": false,
  "human_override_requested": true,
  "human_override_response": null,
  "reasoning_trace": [
    "Device reachable",
    "Tier 3 response recommended"
  ],
  "created_at": "2026-08-31T02:02:00Z",
  "audit": {
    "entry_id": "response-audit-001",
    "incident_id": "INC-1835",
    "cluster_id": "cluster-desert-042",
    "severity_tier": 3,
    "network_grant": null,
    "network_denied": null,
    "actuation_result": "not_executed",
    "logged_at": "2026-08-31T02:02:01Z"
  }
}
```

### Response Agent field table

| JSON path | Description | Type/format | Required | Allowed values/range | Example | AquaPulse destination |
| --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | Contract version | string | Optional | `1.0` | `"1.0"` | `agent_runs.contract_version` |
| `result_id` | Recommendation id | string | Required | Unique per `response_agent` | `"response-result-001"` | `external_result_id`; idempotency `response:{result_id}` |
| `incident_id` | External or AquaPulse incident id | string | Required | Any string. `INC-1835` maps if it is a known public id **and** a mapping row exists (AquaPulse does not guess) | `"INC-1835"` | `external_incident_id`; optional FK to `incidents` |
| `cluster_id` | External cluster | string | Required | Any string | `"cluster-desert-042"` | `external_cluster_id` |
| `device_id` | External device / valve | string | Required | Any string | `"valve-neom-north-01"` | `external_device_id` |
| `severity_tier` | Agent severity | integer | Required | `1`, `2`, `3` | `3` | Stored + UI labels |
| `reachability` | Agent reachability snapshot | object | Optional | Unconstrained object | `{"reachable": true}` | `agent_response_recommendations.reachability` |
| `reachability.device_id` | Device checked | string | Optional | Any string | `"valve-neom-north-01"` | Stored if present |
| `reachability.reachable` | Reachable flag | boolean | Optional | `true` / `false` | `true` | Stored if present |
| `reachability.checked_at` | Check time | date-time | Optional | ISO-8601 | `"2026-08-31T02:01:00Z"` | Stored if present |
| `reachability.raw_signal_quality` | Reported signal | string or number | Optional | Unconstrained | `"GOOD"` | Stored if present |
| `reachability.status` | Fixture convention | string | Optional | Fixtures use `REACHABLE` / `UNREACHABLE` | `"REACHABLE"` | Stored if present |
| `decision` | Recommended action | string enum | Required | See decisions below | `"AUTONOMOUS_ISOLATE"` | `decision`; Agent Audit; Integrations |
| `notification_sent` | Agent-reported notify | boolean | Optional | Default `false` | `false` | Overridden to `false` on the public recommendation record |
| `valve_command_sent` | Agent-reported command | boolean | Optional | Default `false` | `false` | Stored; `valve_command_verified` stays `false` |
| `valve_command_confirmed` | Agent-reported confirm | boolean | Optional | Default `false` | `false` | Stored; unverified |
| `human_override_requested` | Agent asked for a human | boolean | Optional | Default `false` | `true` | Stored; not approval |
| `human_override_response` | Agent-reported human reply | string or null | Optional | Any string or null | `null` | Stored; not approval |
| `reasoning_trace` | Agent-provided steps | array or object | Optional | Any list or object. Hidden chain-of-thought must not be sent | `["Device reachable"]` | Agent Audit, labelled unverified |
| `created_at` | Agent result time | date-time | Required | ISO-8601 | `"2026-08-31T02:02:00Z"` | Payload |
| `audit` | Optional audit companion | object or null | Optional | `ResponseAuditEntryV1` | see example | `response_payload` |
| `audit.entry_id` | Audit id | string | Required if `audit` present | Any string | `"response-audit-001"` | Payload |
| `audit.incident_id` | Audit incident | string | Required if `audit` present | Any string | `"INC-1835"` | Payload |
| `audit.cluster_id` | Audit cluster | string | Required if `audit` present | Any string | `"cluster-desert-042"` | Payload |
| `audit.severity_tier` | Audit severity | integer | Required if `audit` present | Any integer in schema; use `1`–`3` | `3` | Payload |
| `audit.network_grant` | QoD grant snapshot | object or null | Optional | See `NetworkGrant` rows | `null` | Payload; never actuation authority |
| `audit.network_grant.granted` | Grant flag | boolean | Optional | Default `false` | `false` | Payload |
| `audit.network_grant.expires_at` | Grant expiry | date-time or null | Optional | Datetime or null | `null` | Payload |
| `audit.network_grant.grant_id` | Grant id | string or null | Optional | Any string or null | `null` | Payload |
| `audit.network_grant.data_mode` | Grant provenance | string | Optional | Default `mock` | `"mock"` | Payload |
| `audit.network_denied` | QoD denial snapshot | object or null | Optional | See `NetworkDenied` rows | `{"denied": true, "reason": "camara_disabled"}` | Payload |
| `audit.network_denied.denied` | Denied flag | boolean | Optional | Default `true` | `true` | Payload |
| `audit.network_denied.reason` | Denial reason | string or null | Optional | Fixtures use `camara_disabled` | `"camara_disabled"` | Payload |
| `audit.network_denied.data_mode` | Denial provenance | string | Optional | Default `mock` | `"mock"` | Payload |
| `audit.actuation_result` | Actuation note | **string or null** | Optional | String, not an object | `"not_executed"` | Payload |
| `audit.logged_at` | Audit write time | date-time | Required if `audit` present | ISO-8601 | `"2026-08-31T02:02:01Z"` | Payload |
| `extensions` | Extra non-safety fields | object | Optional | Safety-critical extras are rejected | `{}` | Payload |
| `audit_entry` | Alternate envelope name | object | **Not accepted** | — | — | Rejected / ignored as extras; required result fields then fail |
| `operator_message` | Operator text | string | **Not accepted as a first-class field** | — | `"Critical anomaly requires operator attention."` | Not stored |
| `error` | Envelope error | string or null | **Not accepted as a first-class field** | — | `null` | Not stored |

Known decisions:

```text
LOG_ONLY
ALERT_AND_AWAIT
AUTONOMOUS_ISOLATE
ESCALATE_UNREACHABLE
```

Severity mapping:

| Value | Meaning |
| ---: | --- |
| `1` | `TIER_1_MONITOR` |
| `2` | `TIER_2_ALERT` |
| `3` | `TIER_3_AUTONOMOUS` |

AquaPulse display labels for the same integers are listed in the Investigation section.

Safety-critical field names (`decision`, `severity_tier`, `valve_command_sent`, `valve_command_confirmed`, `incident_id`, `human_override_response`, `notification_sent`) must not appear as malformed extras. Unknown **non-dangerous** fields go to `extensions`.

Response Agent results appear in:

* Integration Readiness (`/integrations`) and recommendation detail (`/integrations/recommendations/:id`)
* Agent Audit Trail (`/agent-audit`, `/agent-audit/runs/:runId`)
* Incident Details **only after** `incident_id` is mapped and `incident_attached` is true. The current Incident Details page still shows the seeded `agent_investigation_summary` field; it does not yet render a live recommendation card
* Operations Center when a mapped incident is already in the human response workflow. Ingest does not create operations tasks and does not resolve the incident

---

## Endpoint and headers

| Agent | Method | Endpoint | Content-Type | Idempotency identifier |
| --- | --- | --- | --- | --- |
| Investigation Agent | `POST` | `/api/integrations/agents/investigation/v1/results` | `application/json` | Intended: `batch_id` + `anomaly_id`. **Route not implemented.** Service today: key `investigation:{batch_id}`; unique `anomaly_id` |
| Investigation Agent | `POST` | `/api/integrations/agents/contracts/investigation/v1/validate-response` | `application/json` | None (validation only) |
| Response Agent | `POST` | `/api/integrations/agents/response/v1/results` | `application/json` | Intended: `entry_id` + `result_id`. **Route not implemented.** Service today: key `response:{result_id}` |
| Response Agent | `POST` | `/api/integrations/agents/contracts/response/v1/validate-response` | `application/json` | None (validation only) |

Documented headers for the future ingest routes:

```http
Content-Type: application/json
X-Idempotency-Key: <unique-key>
```

**Real behavior today:** no FastAPI route reads `X-Idempotency-Key`. The header is optional in the sense that it is ignored, because ingest HTTP does not exist. When the Python ingest methods run, `idempotency_key` is an optional function argument.

| Situation | Current service behavior |
| --- | --- |
| Same Investigation `batch_id` (default key) | Returns the existing `AgentRunDetail`. No second run |
| Same Investigation `anomaly_id` with a new batch | `409` / `agent_result_duplicate` |
| Same Response `result_id` (default key or unique constraint) | Existing run returned, or `409` / `agent_result_duplicate` |
| Header `X-Idempotency-Key` on any current HTTP route | Not bound; unused |

---

## Expected API responses

Structured AquaPulse errors always look like:

```json
{
  "detail": {
    "message": "The investigation response was rejected.",
    "code": "agent_result_rejected"
  }
}
```

Validation routes that fail contract checks use `code` values such as `agent_contract_mismatch`, `agent_invalid_response`, or `agent_schema_version_unsupported`.

### Intended ingest success (`202 Accepted`) — not implemented yet

When the ingest routes exist, the intended body is:

```json
{
  "status": "accepted",
  "agent": "investigation_agent",
  "run_id": "AGRUN-000206",
  "created": 3,
  "duplicates": 0,
  "unmapped_ids": [
    "cluster-desert-042",
    "seg-neom-north-01",
    "valve-neom-north-01"
  ]
}
```

That shape is **not** returned by any current route.

### Current validation success (`200 OK`)

`POST /api/integrations/agents/contracts/investigation/v1/validate-response` and the Response equivalent:

```json
{
  "valid": true,
  "schema_version": "1.0",
  "errors": [],
  "warnings": [],
  "side_effects": {
    "external_request": false,
    "incident_created": false,
    "detection_mutated": false,
    "notification_sent": false,
    "valve_executed": false
  }
}
```

### Current persist success (service only)

`ingest_*` returns `AgentRunDetail` (this would be a `200` body if it were exposed):

```json
{
  "run_id": "AGRUN-000206",
  "agent_type": "investigation_agent",
  "status": "succeeded",
  "source_type": "investigation_batch",
  "source_public_id": "batch-2026-08-31-001",
  "started_at": "2026-09-01T07:45:00Z",
  "completed_at": "2026-09-01T07:45:01Z",
  "duration_ms": 12,
  "data_mode": "simulated",
  "mapping_warning_count": 3,
  "error_code": null,
  "correlation_id": "9c2f0d3e-4b11-4c22-8d33-aaaaaaaaaaaa",
  "idempotency_key": "investigation:batch-2026-08-31-001",
  "contract_version": "1.0",
  "request_payload": { "batch_id": "batch-2026-08-31-001" },
  "response_payload": {},
  "validation_errors": [],
  "mapping_warnings": [
    {
      "code": "agent_identity_unmapped",
      "entity_type": "sensor_cluster",
      "external_id": "cluster-desert-042",
      "message": "No configured mapping exists for this external identity."
    }
  ],
  "error_message": null
}
```

Unmapped IDs are **accepted with warnings**. They are not silently discarded.

### Status table

| Outcome | HTTP | Code | Notes |
| --- | --- | --- | --- |
| Intended ingest success | `202 Accepted` | — | **Not implemented** |
| Validation success | `200 OK` | — | Implemented |
| Persist success (service) | no HTTP | — | Returns `AgentRunDetail` |
| Invalid payload | `422 Unprocessable Entity` | `agent_result_rejected` (ingest) or `agent_contract_mismatch` / `agent_invalid_response` (validate) | Transaction rolled back on ingest |
| Unsupported `schema_version` | `422` | `agent_schema_version_unsupported` | Only when `schema_version` is present and not `1.0` |
| Duplicate `anomaly_id` / `result_id` | `409` | `agent_result_duplicate` | Service ingest only |
| Same idempotency key | existing run returned | — | Not a new row |
| Ingestion HTTP disabled / missing | no route | — | Client sees FastAPI `404` `{ "detail": "Not Found" }` today, **not** `503` |
| `AGENT_RESULT_INGEST_ENABLED=false` | flag only | — | Shown on readiness; not enforced by ingest methods |
| Agent execution | `503` | `agent_execution_disabled` | `POST /api/integrations/agents/{agent_code}/execute` |
| Agent row missing during ingest | `503` | `agent_not_configured` | Service ingest only |
| Unmapped identities | success + warnings | `agent_identity_unmapped` | Inside `mapping_warnings`, not a hard failure |

---

## ID mapping

AquaPulse public IDs look like `DET-000001`, `INC-1835`, `SNS-HBR-007`.

Agent IDs often look like:

```text
cluster-desert-042
seg-neom-north-01
valve-neom-north-01
```

Rules:

* Unknown external IDs are accepted and stored as `unmapped` (or `partial` if some of cluster / segment / valve mapped).
* AquaPulse **never guesses** a mapping (including the seeded NEOM demo clusters `cluster-desert-042`–`044`).
* Unmapped results remain visible in Agent Audit and Integrations.
* They cannot automatically attach to an AquaPulse asset, detection or incident.
* Teams may later provide an identity-mapping file.

Example file (already in the repo):

```text
plateform/backend/contracts/agents/mappings.example.json
```

Format: a JSON **array** of objects.

```json
[
  {
    "provider": "investigation_agent",
    "entity_type": "sensor_cluster",
    "external_id": "cluster-example-001",
    "internal_entity_type": "detection",
    "internal_public_id": "DET-000001",
    "enabled": true,
    "metadata": {"note": "Example only. Do not guess NEOM demo IDs."}
  }
]
```

Allowed `entity_type` and `internal_entity_type` values:

```text
sensor_cluster
sensor
segment
valve
device
incident
detection
```

Import (from `plateform/backend/` with the virtual environment active):

```bash
python -m app.scripts.import_identity_mappings --file contracts/agents/mappings.example.json
```

Investigation ingest resolves `sensor_cluster`, `segment`, `valve` (`associated_valve_id`) and `detection` (`anomaly_id`). Response ingest resolves `incident`, `sensor_cluster`, then `device` and, if needed, `valve`.

---

## Complete cURL examples

Do not send API keys, tokens, raw MSISDNs or operator phone numbers.

The ingest URLs will fail with HTTP `404` until those routes are implemented. The validate URLs work today.

### Investigation Agent — Bash (validate, implemented)

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/integrations/agents/contracts/investigation/v1/validate-response" \
  -H "Content-Type: application/json" \
  -d @plateform/backend/contracts/agents/investigation/v1/valid-response.json
```

### Investigation Agent — Windows PowerShell (validate, implemented)

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/integrations/agents/contracts/investigation/v1/validate-response" `
  -ContentType "application/json" `
  -InFile "plateform\backend\contracts\agents\investigation\v1\valid-response.json"
```

### Investigation Agent — Bash (intended ingest — not implemented yet)

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: investigation-batch-2026-08-31-001" \
  -d @plateform/backend/contracts/agents/investigation/v1/valid-response.json
```

### Investigation Agent — Windows PowerShell (intended ingest — not implemented yet)

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/integrations/agents/investigation/v1/results" `
  -ContentType "application/json" `
  -Headers @{ "X-Idempotency-Key" = "investigation-batch-2026-08-31-001" } `
  -InFile "plateform\backend\contracts\agents\investigation\v1\valid-response.json"
```

### Response Agent — Bash (validate, implemented)

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/integrations/agents/contracts/response/v1/validate-response" \
  -H "Content-Type: application/json" \
  -d @plateform/backend/contracts/agents/response/v1/valid-alert-and-await.json
```

### Response Agent — Windows PowerShell (validate, implemented)

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/integrations/agents/contracts/response/v1/validate-response" `
  -ContentType "application/json" `
  -InFile "plateform\backend\contracts\agents\response\v1\valid-alert-and-await.json"
```

### Response Agent — Bash (intended ingest — not implemented yet)

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/integrations/agents/response/v1/results" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: response-result-001" \
  -d @plateform/backend/contracts/agents/response/v1/valid-alert-and-await.json
```

### Response Agent — Windows PowerShell (intended ingest — not implemented yet)

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/integrations/agents/response/v1/results" `
  -ContentType "application/json" `
  -Headers @{ "X-Idempotency-Key" = "response-result-001" } `
  -InFile "plateform\backend\contracts\agents\response\v1\valid-alert-and-await.json"
```

Offline fixture check (no HTTP):

```bash
cd plateform/backend
python -m app.scripts.validate_agent_fixture --agent investigation --file contracts/agents/investigation/v1/valid-response.json
python -m app.scripts.validate_agent_fixture --agent response --file contracts/agents/response/v1/valid-alert-and-await.json
```

---

## Information not supplied by these agents

The two current formats do not provide:

* Estimated water loss
* NRW
* Generic device health score
* Billing data
* Consumption data
* Verified physical repair
* Platform-verified valve execution

AquaPulse must not invent or display these as agent-provided facts. Dashboard water-loss and health figures come from platform telemetry and seed data, not from these agents.

---

## Safety notes

* AquaPulse does not implement the agents.
* Agent orchestration is external.
* Agent outputs are validated and stored.
* `confirmed_anomaly` is an agent assessment.
* Confidence is not automatically a calibrated probability.
* Agent-reported valve actions are not automatically platform verified.
* Receiving a result must not automatically resolve an incident.
* Secrets, API keys, raw MSISDNs and operator phone numbers must not be sent.
* Payloads are sanitized / redacted before storage (`redact_payload`, `sanitize_payload`). Keys such as `api_key`, `token`, `password`, `operator_contact`, `device_msisdn` and internal URLs are stripped or replaced.
* `device_msisdn` is a fictional device SIM identity. It is **not** `operator_contact`.
* CAMARA `network_grant` is not authorization to close a valve.
* Human approval must occur before any future physical execution.

---

## Network Health scope

> Network Health is outside the scope of these two agent integrations and will be integrated separately. This document does not define a Network Agent endpoint or contract.

---

## Integration checklist

1. Implement the documented JSON output (`InvestigationBatchResultV1` raw batch or wrapper; flat `ResponseResultV1`).
2. Start the agent service.
3. Enable AquaPulse result ingestion locally (`AGENT_RESULT_INGEST_ENABLED=true` on the AquaPulse host). The HTTP ingest routes still need to be added before this flag has an HTTP effect.
4. POST a test payload to the validation routes first, then to the ingest routes once they exist.
5. Verify the intended `202 Accepted` response after ingest HTTP is implemented. Today expect `200` on validate, or `404` on the ingest URLs.
6. Check duplicate / idempotency behavior (`batch_id` / `anomaly_id`, `result_id`).
7. Resolve ID mapping warnings with `import_identity_mappings`.
8. Verify the result in Agent Audit.
9. Verify mapped results in Detection Details or, when attached, Incident Details.
10. Run the existing contract tests from `plateform/backend/`:

```bash
pytest tests/test_agent_integration.py
python -m app.scripts.validate_agent_fixture --agent investigation --file contracts/agents/investigation/v1/valid-response.json
python -m app.scripts.validate_agent_fixture --agent response --file contracts/agents/response/v1/valid-alert-and-await.json
```
