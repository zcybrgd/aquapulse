# AquaPulse agent integration guide

This is the handoff for the Investigation Agent, Network Management Agent and Response Agent teams.

You do **not** need to change AquaPulse’s database, migrations, or frontend.

AquaPulse is prepared to connect later. **Agent execution is disabled.**

## Authoritative responsibilities

```text
Sensor readings
→ Lightweight anomaly detection model
→ Anomaly Investigation Agent
→ Network Management Agent
→ Response Agent
→ Platform audit and monitoring
```

| Component | Owner |
| --- | --- |
| Candidate detection | Lightweight model (existing deterministic rules) |
| Confirmation, classification, confidence, severity | Investigation Agent |
| Connectivity, CAMARA, QoD | Network Management Agent |
| Response recommendation / action request | Response Agent |
| Persistence, UI, mapping, audit, safety | AquaPulse |

AquaPulse must not duplicate those agent decisions. Screening priority is not final severity.

## Current contracts

### Investigation Agent (confirmed format)

Team output fields: `batch_id`, `analysis_timestamp`, `total_clusters_analyzed`, `anomalies_detected_count`, `investigated_threats`.

Each threat: `anomaly_id`, `sensor_cluster_id`, `segment_id`, `classification`, `severity_tier`, `network_status`, `physical_deviations`, `criticality_metrics`, `operator_justification`, `confidence_score`.

Classifications: `confirmed_anomaly`, `confirmed_instrument_fault`.

Mock fixtures persist `cluster-desert-042`, `cluster-desert-043` and `cluster-desert-044` exactly. They remain unmapped until a real identity mapping exists.

### Response Agent (confirmed format)

Graph, stored exactly as reported:

```text
reachability_check → llm_response_planner → execute_response → human_override → audit_writer
```

Decisions: `LOG_ONLY`, `ALERT_AND_AWAIT`, `AUTONOMOUS_ISOLATE`, `ESCALATE_UNREACHABLE`.

AquaPulse does not rewrite this graph. A separate platform safety result may block `AUTONOMOUS_ISOLATE`. Mock execution is unverified: valve state unchanged, notification not sent.

### Network Management Agent (contract pending)

The final schema is not available. AquaPulse stores only draft mock event logs with `schema_version: draft-unconfirmed`. Presentation labels: `connectivity_check`, `qod_requested`, `qod_granted`, `qod_denied`, `qod_released`, `agent_error`.

Every Network page shows: `Network Agent contract awaiting team confirmation`.

Mock-to-real replacement path: keep the same audit event table and adapters; replace draft envelopes with the confirmed contract without adding an AquaPulse decision engine.

## What you implement

1. Expose the documented HTTP endpoints.
2. Give AquaPulse a base URL.
3. Set the matching environment variables on the AquaPulse host.
4. Run the supplied contract-check command.
5. Ask an AquaPulse operator to enable the feature flag later. There is no public enable button.

## Investigation Agent

```text
GET  /health
GET  /v1/contract
POST /v1/investigate
```

Copy `backend/examples/investigation_agent_wrapper.py` around your existing module.

Contract files: `backend/contracts/agents/investigation/v1/`.

## Response Agent

```text
GET  /health
GET  /v1/contract
POST /v1/recommend-response
```

The path is `recommend-response`, not `execute`. AquaPulse retains execution authority.

Copy `backend/examples/response_agent_wrapper.py` around your existing module.

If your graph already uses another path, AquaPulse can set `RESPONSE_AGENT_RECOMMEND_PATH`.

## Environment variables (AquaPulse side)

```env
AGENT_INTEGRATION_ENABLED=false
INVESTIGATION_AGENT_ENABLED=false
INVESTIGATION_AGENT_MODE=disabled
INVESTIGATION_AGENT_URL=
RESPONSE_AGENT_ENABLED=false
RESPONSE_AGENT_MODE=disabled
RESPONSE_AGENT_URL=
```

Do not put `GROQ_API_KEY` in AquaPulse. Your agent owns its LLM configuration.

## Contract check

From `backend/` with the virtual environment active:

```bash
python -m app.scripts.check_agent_contract --agent investigation --base-url http://127.0.0.1:9001
python -m app.scripts.check_agent_contract --agent response --base-url http://127.0.0.1:9002
```

Offline fixture check:

```bash
python -m app.scripts.validate_agent_fixture --agent investigation --file contracts/agents/investigation/v1/valid-response.json
python -m app.scripts.validate_agent_fixture --agent response --file contracts/agents/response/v1/valid-alert-and-await.json
```

A non-zero exit code means the payload is incompatible.

## Identity mapping

AquaPulse uses public IDs such as `DET-000001`, `INC-1835`, `SNS-HBR-007`.

Your agents may use IDs such as `cluster-desert-042`.

Unknown IDs are stored as `unmapped`. AquaPulse never guesses. Import mappings later with:

```bash
python -m app.scripts.import_identity_mappings --file mappings.json
```

## Safety rules you can rely on

- Investigation results are advisory evidence.
- Response results are recommendations.
- Agent severity does not authorize actuation.
- CAMARA network permission does not authorize valve control.
- Human approval must occur before any future physical execution.
- AquaPulse remains the authority for incidents and infrastructure actions.

A wrapper example never sends a real notification or valve command.

## Device MSISDN is not operator contact

AquaPulse devices may have a fictional demonstration `device_msisdn` (E.164 SIM identity). That field is **not** `operator_contact`.

Do not map:

```text
device_msisdn → operator_contact
```

Contract version `1.0` is unchanged for Investigation and Response. The Network Management Agent contract remains unconfirmed (`draft-unconfirmed`). A future authorized contract may receive device public ID, zone public ID (`ZONE-HBR`), coordinates, location label, and MSISDN only when explicitly required. Until that contract is confirmed, those fields are not added to external request or response schemas. Public APIs return only a masked MSISDN.

Reasoning shown in the Agent Audit Trail is **agent-provided reasoning — not independently verified**. Hidden LLM chain-of-thought is not stored or displayed.
