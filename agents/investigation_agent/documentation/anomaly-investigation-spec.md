# Technical Specification: Anomaly Investigation Agent (AIA)
**AquaPulse Smart Water Intelligence**  
*Document Version: 1.0 (Implementation-Ready)*

---



## 1. Executive Summary & Core Objective
The **Anomaly Investigation Agent (AIA)** is a crucial, high-intelligence agent.In water-stressed regions like MENA, remote IoT leak-detection sensors frequently experience connectivity drops due to extreme temperatures (exceeding 50°C), making traditional static rule-engines highly unreliable.

The primary objective of the AIA is to ingest raw anomalous events from the telemetry stream, programmatically disambiguate between physical pipeline failures and cellular network degradation using Nokia Network-as-Code (NaC) CAMARA APIs, evaluate physical asset risk, and deliver a highly structured decision payload to the downstream **Network Management Agent** in under 30 seconds.

---

## 2. End-to-End Workflow

The agent operates in a sequential, deterministic-to-probabilistic pipeline. Each step is designed to isolate variables, minimizing expensive LLM calls and API overhead.

```
+----------------------------------------------------------------------------------------------------+
|                                      End-to-End AIA Workflow                                       |
+----------------------------------------------------------------------------------------------------+
|  [Telemetry Stream Anomaly]                                                                        |
|              │                                                                                     |
|              ▼                                                                                     |
|  Step 1: Ingestion & Trigger ─────────────────► [Packs Raw Telemetry & Sensor IDs]                 |
|              │                                                                                     |
|              ▼                                                                                     |
|  Step 2: Network Disambiguation ──────────────► [Queries CAMARA APIs (Device Status/Reachability)] |
|              │                                  [Evaluates local network degradation patterns]     |
|              ▼                                                                                     |
|  Step 3: Risk & Criticality Assessment ───────► [Evaluates pipeline asset metadata & leak history] |
|              │                                  [Computes severity and assigns Risk Tier 1/2/3]    |
|              ▼                                                                                     |
|  Step 4: Output Compilation ──────────────────► [Generates JSON payload & LLM-based Operator Memo] |
|              │                                                                                     |
|              ▼                                                                                     |
|  [To Network Management Agent]                                                                     |
+----------------------------------------------------------------------------------------------------+
```

### Step 1: Ingestion and Triggering

*   **Information Processed:** Raw anomalous telemetry values, timestamp, and unique sensor cluster metadata.
*   **Reasoning/Analysis:** Deterministic threshold monitoring. The ingestion engine flags readings that drift more than a pre-configured percentage from the rolling baseline (typically a sudden pressure drop or flow spike)
*   **Required Data:** Telemetry event containing `sensor_cluster_id`, current `pressure_psi`, current `flow_rate_lps`, and `ambient_temp_c`.
*   **Deliverable:** A structured, parsed ingestion payload initialized in the Agent's short-term state memory.

### Step 2: Network Disambiguation (Network Guardian Layer)
*   **Information Processed:** Real-time cellular registration, packet loss rates, and local ambient heat conditions.
*   **Reasoning/Analysis:** The agent must differentiate between a physical pipe burst and a sensor going silent due to extreme desert heat. It queries Nokia NaC's CAMARA APIs to verify the physical connection. If the API returns a degraded or disconnected state while ambient temperatures are above 50°C, it cross-references the historical zone degradation matrix to identify if a cell tower is under thermal strain.
*   **Required Data:** Nokia NaC credentials, CAMARA integration endpoints, and historical zone-connectivity profiles stored in TimescaleDB.
*   **Deliverable:** Disambiguation classification: `"confirmed_anomaly"`, `"likely_connectivity_artifact"`, or `"insufficient_data — escalate monitoring"`.

### Step 3: Risk and Criticality Assessment (Risk Assessment Layer)
*   **Information Processed:** Disambiguation status, geographic proximity to water reservoirs, population served, and past leak-pattern data.
*   **Reasoning/Analysis:** If the anomaly is confirmed, the agent computes an asset-impact score. High deviation near a critical regional reservoir yields a high-risk score, whereas a minor drip in an auxiliary branch is classified as low-risk.
*   **Required Data:** Asset criticality lookup table, GIS mapping layers, and historical incident records.
*   **Deliverable:** Severity Tier (`Tier 1`: Minor/Monitor, `Tier 2`: Moderate, `Tier 3`: Catastrophic).

### Step 4: Output Compilation
*   **Information Processed:** Classification status, computed severity tier, network status data, and reasoning notes.
*   **Reasoning/Analysis:** An LLM processes the structured context to generate a highly professional, concise "Operator Memo" explaining the rationale, while a validation layer ensures the JSON schema is perfectly structured.
*   **Required Data:** Pydantic validation schema, LLM Prompt Template.
*   **Deliverable:** Validated, structured JSON payload published directly to the next agent in the pipeline.

---

## 3. Input Specification

The AIA is triggered by a JSON event delivered via the ingestion API gateway.

### Data Fields Specification
*   `anomaly_id` (String, Required): Unique UUID4 generated by the stream processor.
*   `sensor_cluster_id` (String, Required): Unique identifier of the sensor cluster.
*   `timestamp` (String, Required): ISO 8601 UTC timestamp of the detection.
*   `telemetry_data` (Object, Required):
    *   `pressure_psi` (Float, Required): Current pressure reading.
    *   `baseline_pressure_psi` (Float, Required): Standard pressure baseline for this time/day.
    *   `flow_rate_lps` (Float, Required): Current flow rate in liters per second.
    *   `baseline_flow_rate_lps` (Float, Required): Standard flow baseline.
    *   `ambient_temp_c` (Float, Required): Ambient temperature at the cluster location.
*   `network_metadata` (Object, Optional):
    *   `signal_strength_dbm` (Integer, Optional): Signal strength reported by edge gateway.
    *   `packet_loss_pct` (Float, Optional): Packet drop rate over the last 1 minute.

### Example JSON Input
```json
{
  "anomaly_id": "anom-987234-xyz",
  "sensor_cluster_id": "cluster-desert-042",
  "timestamp": "2026-08-29T09:15:30Z",
  "telemetry_data": {
    "pressure_psi": 28.4,
    "baseline_pressure_psi": 45.0,
    "flow_rate_lps": 112.5,
    "baseline_flow_rate_lps": 80.0,
    "ambient_temp_c": 51.5
  },
  "network_metadata": {
    "signal_strength_dbm": -105,
    "packet_loss_pct": 12.5
  }
}
```

---

## 4. Investigation and Risk Assessment Logic

The agent uses a robust dual-stage decision matrix to isolate network failures and evaluate physical severity.

```
                              [Incoming Anomaly Event]
                                         │
                                         ▼
                             [Query CAMARA Device Status]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼ (Online)                                  ▼ (Offline/Degraded)
         [Device Reachability API]                       [Query Temp & History]
                   │                                           │
         ┌─────────┴─────────┐                     ┌───────────┴───────────┐
         ▼ (Reachable)       ▼ (Unreachable)       ▼ (Temp > 50°C)         ▼ (Temp < 50°C)
  [CONFIRMED ANOMALY]      [INSUFFICIENT DATA]   [LIKELY CELL FAILURE]   [CONFIRMED ANOMALY]
         │                                       (Thermal degradation)   (Hardware/Power cut)
         ▼
[Calculate Risk & Tier 1/2/3]
```

### Network vs. Equipment Failure Disambiguation
1.  **Direct API Interrogation:** Upon receiving the anomaly, the AIA calls the **CAMARA Device Status API**.
    *   If Device Status is `disconnected`, the agent checks the `ambient_temp_c`. If temperature $\ge 50^\circ\text{C}$ and historical cellular degradation in this sector matches, the event is classified as `"likely_connectivity_artifact"`.
    *   If Device Status is `connected`, the agent calls the **CAMARA Device Reachability API** to confirm if a two-way command channel can be established (crucial for sending isolation commands to actuators).
2.  **Transient/Inconsistent Behavior:** If Device Reachability is fluctuating or reporting errors, the classification is flagged as `"insufficient_data — escalate monitoring"`, which bypasses full alert sequences but triggers an immediate instruction to increase polling frequency to capture higher-resolution data.

### Risk Tiering Logic
Once the anomaly is `"confirmed_anomaly"`, the agent calculates the physical severity by combining telemetry deviation with asset criticality:

$$\text{Pressure Drop Ratio } (\Delta P) = \frac{P_{\text{baseline}} - P_{\text{current}}}{P_{\text{baseline}}}$$

$$\text{Flow Surge Ratio } (\Delta Q) = \frac{Q_{\text{current}} - Q_{\text{baseline}}}{Q_{\text{baseline}}}$$

The segment is evaluated against metadata loaded from the pipeline criticality reference table:
*   `criticality_score` ($C$): Integer scale $1$ (Low) to $3$ (High). $C=3$ represents segments adjacent to main reservoirs, critical blending stations, or serving major populations (e.g., NEOM main residential zone).

#### Classification Criteria:
*   **Tier 1 (Minor / Monitor Only):** $\Delta P < 15\%$, $\Delta Q < 20\%$, and $C \le 1$.
    *   *System Action:* Write to system log, update dashboard, no network intervention needed.
*   **Tier 2 (Moderate / Escalation Required):** $15\% \le \Delta P < 35\%$ OR $C = 2$.
    *   *System Action:* Requires Quality on Demand (QoD) activation to stabilize telemetry stream, and immediately triggers human operator notifications.
*   **Tier 3 (Catastrophic / Autonomous Intervention):** $\Delta P \ge 35\%$ AND $C = 3$.
    *   *System Action:* Requires dedicated network slicing, triggers autonomous valve isolation commands, and alerts operators with override capabilities.

---

## 5. AI/LLM Architecture

The agent is built using a multi-layer framework (LangChain/LangGraph) utilizing Model Context Protocol (MCP) servers for secure, structured tool usage.

```
┌────────────────────────────────────────────────────────┐
│               Anomaly Investigation Agent              │
│                                                        │
│  ┌─────────────────┐             ┌──────────────────┐  │
│  │   LangGraph /   │             │   Pydantic State │  │
│  │   LangChain     │◄───────────►│   Memory Context │  │
│  └────────┬────────┘             └──────────────────┘  │
│           │                                            │
│           ▼ (MCP Server Call)                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │                   Tool Directory                 │  │
│  │  - get_device_status()    - query_timescale_db() │  │
│  │  - get_reachability()     - get_asset_metadata() │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Deterministic vs. Heuristic (LLM) Boundary
To ensure sub-second response times, raw calculations are kept strictly deterministic, reserving the LLM for unstructured, high-level reasoning.
*   **Deterministic Execution (Python):** Raw mathematical calculation of $\Delta P$ and $\Delta Q$; direct execution of CAMARA API wrappers; checking hard safety limits (e.g., forcing a Tier 3 if pressure drops $\ge 50\%$).
*   **LLM reasoning (GPT-4o or Claude 3.5 Sonnet):** Parsing multi-signal contextual patterns (e.g., correlating high heat + high packet loss + mild pressure drop to spot a slow, hidden thermal leak), and synthesizing the natural language operator memo.

### Context & Memory Management
*   **Short-Term Context:** A sliding memory window is populated for each active investigation. This holds the last $N$ readings (usually 10 minutes of telemetry) and the last $N$ network-state observations. No long-term, vector-based RAG is used for the execution layer to preserve speed, but historic incident templates are accessible as standard structured references.

### Safety Guardrails
*   **Hard-Coded Safe Ceiling:** The LLM can never override a deterministic Tier 3 trigger or initiate direct mechanical action.
*   **Validation Layer:** Pydantic models validate every LLM tool call and the final output schema.
*   **Cost & Rate-Limiting:** API gateways throttle calls per sensor cluster to prevent runaway loops or high billing under telemetry noise.

---

## 6. Output Specification

Upon completion, the AIA produces a strictly validated JSON payload for the **Network Management Agent**.

### Structured JSON Schema (Pydantic v2 format)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AIA_Output_Payload",
  "type": "object",
  "properties": {
    "anomaly_id": { "type": "string", "format": "uuid" },
    "sensor_cluster_id": { "type": "string" },
    "investigation_timestamp": { "type": "string", "format": "date-time" },
    "classification": { 
      "type": "string", 
      "enum": ["confirmed_anomaly", "likely_connectivity_artifact", "insufficient_data"] 
    },
    "severity_tier": { "type": "integer", "enum": [1, 2, 3] },
    "criticality_metrics": {
      "type": "object",
      "properties": {
        "segment_id": { "type": "string" },
        "criticality_score": { "type": "integer", "minimum": 1, "maximum": 3 },
        "proximity_to_reservoir_m": { "type": "number" },
        "population_served": { "type": "integer" }
      },
      "required": ["segment_id", "criticality_score", "proximity_to_reservoir_m", "population_served"]
    },
    "network_status": {
      "type": "object",
      "properties": {
        "device_online": { "type": "boolean" },
        "device_reachable": { "type": "boolean" },
        "network_degradation_detected": { "type": "boolean" }
      },
      "required": ["device_online", "device_reachable", "network_degradation_detected"]
    },
    "operator_justification": { "type": "string" },
    "confidence_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
  },
  "required": [
    "anomaly_id", "sensor_cluster_id", "investigation_timestamp", 
    "classification", "severity_tier", "criticality_metrics", 
    "network_status", "operator_justification", "confidence_score"
  ]
}
```

### Example JSON Output
```json
{
  "anomaly_id": "anom-987234-xyz",
  "sensor_cluster_id": "cluster-desert-042",
  "investigation_timestamp": "2026-08-29T09:15:32Z",
  "classification": "confirmed_anomaly",
  "severity_tier": 3,
  "criticality_metrics": {
    "segment_id": "seg-neom-north-01",
    "criticality_score": 3,
    "proximity_to_reservoir_m": 120.0,
    "population_served": 45000
  },
  "network_status": {
    "device_online": true,
    "device_reachable": true,
    "network_degradation_detected": false
  },
  "operator_justification": "A major pressure drop of 36.8% was detected at cluster-desert-042, located adjacent to the main NEOM north reservoir. The Nokia CAMARA Device Status API confirms the device is online and fully reachable with no network degradation. Given the high asset criticality and confirmed connectivity, this is classified as a genuine physical failure (Tier 3) requiring immediate autonomous isolation.",
  "confidence_score": 0.98
}
```

---

## 7. Interface Between Agents

To prevent latency and network saturation, the agent communication protocol is asynchronous and highly decoupled.

### Data Flow Pattern
```
[Stream Ingestion] 
       │
       ▼
┌──────────────┐      Structured Payload       ┌─────────────┐
│  Anomaly     ├──────────────────────────────►│   Network   │
│  Invest.     │                               │  Management │
│  Agent (AIA) │◄──────────────────────────────┤ Agent (NMA) │
└──────────────┘       Event Acknowledged      └──────┬──────┘
                                                      │
                                                      ▼
                                              [CAMARA QoS Call]
                                              [Actuator Command]
```

### Data Handoff and Interpretation Rules
1.  **Strict Payload Separation:** Raw pressure log arrays are kept in TimescaleDB. Only the processed `AIA_Output_Payload` is transmitted across agents. This reduces memory overhead and decouples the analysis layer from the orchestration execution.
2.  **Downstream Interpretation:**
    *   `classification == "likely_connectivity_artifact"`: The Network Management Agent (NMA) will bypass any leak alerts, log the incident as a cellular/gateway issue, and schedule a routine telemetry-maintenance ticket.
    *   `severity_tier == 2`: The NMA triggers an immediate **Quality on Demand (QoD) API** priority boost to guarantee continued high-frequency reporting, and sends an SMS/email alert to human field teams.
    *   `severity_tier == 3`: The NMA immediately requests a **Dedicated Network Slice** (covering the sensor corridor and the valve actuator), fires an autonomous isolation command to the motorized valve, and alerts operators.
3.  **Uncertainty & Error Handling:**
    *   If `confidence_score` $< 0.70$ or `classification == "insufficient_data"`, the NMA defaults to a protective fallback state: it triggers a temporary QoD priority boost to stabilize data flow, and immediately requests human operator confirmation rather than taking autonomous physical actions.
    *   If the AIA experiences an internal crash or LLM timeout, a hard-coded fallback event handler generates a default payload of `severity_tier: 2` with a `system_error` flag, forcing human-in-the-loop escalation.

---

## 8. Implementation Roadmap & Testing Plan

This roadmap provides a phased engineering plan for the MVP.

### Phase 1: Environment Setup & Mock Integration (Weeks 1-2)
*   Deploy LangGraph orchestrator container and setup TimescaleDB schemas.
*   Create mockup interfaces for the Nokia NaC endpoints using FastAPIs:
    *   `GET /camara/device-status/v1` -> returns simulated signal health.
    *   `GET /camara/device-reachability/v1` -> returns reachability status.

### Phase 2: Agent Logic & Tool Development (Weeks 3-4)
*   Build Python wrappers for the mock CAMARA endpoints and register them as LangChain tools.
*   Implement deterministic threshold checks and the asset-criticality lookup functions.
*   Write and refine the Agent Prompt Template (see below).

#### System Prompt Template for AIA LLM Reasoning:
```text
You are the AI brain of the AquaPulse Anomaly Investigation Agent (AIA).
Your goal is to investigate anomalous water telemetry signals and determine if they are physical leaks or wireless artifacts.

REASONING PROTOCOL:
1. Review the input telemetry (pressure, flow, ambient temperature).
2. Execute 'get_device_status' and 'get_reachability' tools to inspect network health.
3. If temperature is > 50°C and signal is degraded, cross-reference known heat-degradation histories.
4. Combine pressure/flow anomalies with asset criticality metadata to assign severity Tier 1, 2, or 3.

CRITICAL SAFETY POLICY:
- If pressure drops are >= 50% on High Criticality segments, you MUST classify as Tier 3.
- Never attempt to trigger actuator controls directly. That is the sole responsibility of the Network Management Agent.

You must output your complete analysis wrapped inside the specified JSON format.
```

### Phase 3: Validation, Testing & Evaluation (Weeks 5-6)
To satisfy rigorous industrial reliability, the AIA must be tested under extreme simulation scenarios prior to field pilots.

#### Testing Scenarios:
1.  **Scenario A (True Negative / Cellular Outage):** Simulate 52°C heat, signal dropping to -115dBm, telemetry showing flatlines.
    *   *Expected AIA Output:* `classification: "likely_connectivity_artifact"`, `severity_tier: 1`, `confidence_score` $\ge 0.90$.
2.  **Scenario B (True Positive / Critical Leak):** Simulate 48°C ambient, stable cellular signal, telemetry showing pressure dropping by 40% and flow rate spiking by 50% on a segment adjacent to NEOM North Reservoir.
    *   *Expected AIA Output:* `classification: "confirmed_anomaly"`, `severity_tier: 3`, `confidence_score` $\ge 0.95$.

#### Performance KPIs & Evaluation Metrics:
*   **AIA Processing Latency:** $\le 5.0$ seconds from ingestion to output generation.
*   **False Positive Rate:** $\le 2.0\%$ under network noise and high heat.
*   **JSON Schema Compliance:** 100% of outputs must successfully pass Pydantic schema validation.
