# Technical Specification: Anomaly Investigation Agent (AIA)
**AquaPulse Smart Water Intelligence**  

---

## 1. Executive Summary & Core Objective
The **Anomaly Investigation Agent (AIA)** is the high-intelligence foundational brain of the AquaPulse autonomous water-management system. It merges the active wireless connectivity monitoring with the hydraulic safety assessment into a single, unified agentic service. 

In water-stressed regions like the MENA region, smart water infrastructures suffer from a dual vulnerability: physical pipeline bursts waste precious, energy-intensive desalinated water, while the remote IoT sensors deployed to catch those leaks frequently lose cellular signal due to extreme desert temperatures exceeding 50°C. This causes critical alerts to arrive hours late or get lost entirely. 

Unlike passive rule-engines or disconnected analytics platforms, the AIA treats **all incoming pipeline telemetry and network signals** as a continuous stream of raw logs. The AIA is responsible for:
1.  Ingesting **all logs** (including normal, healthy operations).
2.  Executing **real-time anomaly detection** using combined statistical rules and machine learning (ML) models.
3.  Filtering out normal telemetry to avoid downstream system noise and costly API calls.
4.  Conducting an **active anomaly investigation** using Nokia Network-as-Code (NaC) CAMARA APIs to disambiguate physical asset failures from thermal telecom degradation.
5.  Calculating physical asset risk using pipeline topology and historic baselines.
6.  Emitting a structured, actionable investigation report to the downstream **Network Management Agent (NMA)** in under 30 seconds.

---

## 2. End-to-End Workflow

The AIA operates as a structured pipeline, transitioning from high-volume deterministic filtering to low-frequency agentic reasoning. This guarantees sub-second execution times for normal states while preserving deep LLM reasoning for genuine, high-threat situations.

```
                                      All Raw Infrastructure Logs
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: ANOMALY DETECTION (Deterministic & ML Filtering)                                   │
│                                                                                              │
│                Normal Logs                             Suspicious Logs                       │
│  [Archived directly to TimescaleDB] ◄────────────── [ML & Thresholds] ──────────────────────┐│
└─────────────────────────────────────────────────────────────────────────────────────────────┼┘
                                                                                              │
                                                                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: ANOMALY INVESTIGATION (Agentic Disambiguation)                                     │
│                                                                                              │
│  - Query Nokia NaC CAMARA APIs (Device Reachability Status)                                  │
│  - Correlate extreme ambient temperatures (> 50°C) and network degradation matrices          │
│  - Trend analysis of the last 5-10 telemetry readings (Rate of change of flow and pressure)  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: RISK ASSESSMENT (Hydraulic & Criticality Evaluation)                               │
│                                                                                              │
│  - Cross-reference with docker-compose / Pipeline Topology                                   │
│  - Extract Segment Criticality, Proximity to Reservoirs, and Population Served               │
│  - Classify Threat into Actionable Risk Tiers (Tier 1, Tier 2, Tier 3)                       │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: OUTPUT COMPILATION & HANDOFF (Structured Delivery)                                 │
│                                                                                              │
│  - LLM synthesizes natural-language Operator Memo explaining the root-cause reasoning        │
│  - Validate payload against Pydantic schema; forward ONLY confirmed anomaly results to NMA   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Anomaly Detection (Deterministic & ML Filtering)
*   **Information Processed:** Batched stream of telemetry logs from all deployed sensor clusters. This includes current and trailing telemetry sequences (last 5-10 readings) for pressure, flow rate, and ambient temperature.
*   **Reasoning/Analysis:** The ingestion pipeline runs a dual-layer detection check:
    *   *Deterministic Boundary Check:* Flags immediate violations of static safety bounds (e.g., instant pressure drop of $\ge 15\%$ or flow surge of $\ge 20\%$ within a rolling 5-minute window).
    *   *ML Sequence Scoring:* Passes the 10-step telemetry array through a machine learning model (e.g., an LSTM Autoencoder or Isolation Forest) to evaluate multi-variable deviation. If the reconstruction error or isolation score exceeds dynamically calculated thresholds (which adjust based on time-of-day and ambient temperature baselines), the cluster sequence is flagged as `suspicious`.
*   **Required Data:** The raw telemetry stream containing `sensor_cluster_id`, `readings` (an array of the last 10 records), and current `ambient_temp_c`.
*   **Deliverable:** Normal logs are bypassed and archived to TimescaleDB. Suspicious logs are assigned an `anomaly_id` and promoted to the short-term State Memory of the AIA to initiate active investigation.

### Stage 2: Anomaly Investigation (Agentic Disambiguation)
*   **Information Processed:** Suspicious telemetry sequences, real-time edge gateway status, and environmental variables.
*   **Reasoning/Analysis:** This stage distinguishes between a physical pipe burst and a sensor going offline or transmitting garbage data due to extreme desert heat. The agent invokes the Nokia NaC **CAMARA Device Status** and **Device Reachability** APIs to examine physical connection parameters. If the device is reported as disconnected or unreachable by the network while local temperatures exceed 50°C, the agent cross-references historical regional signal degradation profiles to diagnose thermal base-station degradation.
*   **Required Data:** Nokia NaC integration tokens, CAMARA Device API endpoints, and historical network health patterns.
*   **Deliverable:** Investigation status classification: `confirmed_anomaly` (reachable network, drop in pressure), `likely_connectivity_artifact` (unreachable network under extreme heat), or `insufficient_data` (unstable or fluctuating reachability).

### Stage 3: Risk Assessment (Hydraulic & Criticality Evaluation)
*   **Information Processed:** Verified anomaly data, geographic pipeline topology, downstream valve connectivity, and local population impacts.
*   **Reasoning/Analysis:** For any cluster classified as a `confirmed_anomaly`, the agent maps the sensor cluster ID to its physical pipeline segment within the system topology. It calculates the hydraulic rate of change (slopes of pressure and flow over the last 10 readings) and applies a multi-signal risk matrix. High-velocity drops located near main water reservoirs or serving massive populations (such as residential sectors in NEOM) trigger extreme severity scoring, whereas slow pressure decays in peripheral agricultural lines are scored lower.
*   **Required Data:** Pipeline Network Topology (segment associations, valves, reservoirs, populations) and asset-criticality database indices.
*   **Deliverable:** Physical Severity Score, Target Valve ID, and assigned Actionable Risk Tier (`Tier 1`: Minor, `Tier 2`: Moderate, `Tier 3`: Catastrophic).

### Stage 4: Output Compilation & Handoff
*   **Information Processed:** Investigation classifications, physical deviations, network health diagnostics, and topology assets.
*   **Reasoning/Analysis:** The agent's LLM reasons over the assembled factual context to synthesize a concise, highly professional "Operator Justification Memo" for the SCADA dashboard and audit trail. A Pydantic validation layer formats and enforces the final JSON payload.
*   **Required Data:** System Prompt Template, Pydantic Schema.
*   **Deliverable:** A validated, structured JSON payload delivered to the **Network Management Agent (NMA)** containing only the actionable investigation results of the verified anomalies.

---

## 3. Input Specification

To facilitate full system awareness, the AIA receives an integrated batch payload containing the trailing telemetry windows for all deployed clusters, alongside the physical network topology of the water pipeline infrastructure.

### Input Data Fields
*   `batch_id` (String, Required): Unique UUID4 or structured identifier for the processing batch.
*   `timestamp` (String, Required): ISO 8601 UTC timestamp when the batch was emitted by the stream processor.
*   `telemetry_windows` (Array of Objects, Required): Trailing sequence of readings for every sensor cluster in the network.
    *   `sensor_cluster_id` (String, Required): Unique ID of the sensor cluster.
    *   `network_metadata` (Object, Optional): Trailing cellular metadata.
        *   `signal_strength_dbm` (Integer, Optional): Signal strength of the edge cellular module.
        *   `packet_loss_pct` (Float, Optional): Trailing packet loss percentage.
    *   `readings` (Array of Objects, Required): Sliding sequence of the last 5-10 chronological readings (typically spaced 1 minute apart).
        *   `timestamp` (String, Required): ISO 8601 reading timestamp.
        *   `pressure_psi` (Float, Required): Monitored line pressure.
        *   `flow_rate_lps` (Float, Required): Monitored volumetric flow rate in liters per second.
        *   `ambient_temp_c` (Float, Required): Local temperature at the sensor node.
*   `pipeline_topology` (Object, Required): The structural network topology of the water pipeline system, mapping sensors, segments, valves, and criticality parameters.
    *   `segments` (Array of Objects, Required): Physical pipeline segments.
        *   `segment_id` (String, Required): Unique segment identifier.
        *   `sensor_cluster_id` (String, Required): The cluster physical monitoring node.
        *   `associated_valve_id` (String, Required): The downstream motorized isolation valve ID.
        *   `criticality_score` (Integer, Required): Scale $1$ (Low) to $3$ (High). $C=3$ is high-impact.
        *   `proximity_to_reservoir_m` (Float, Required): Distance in meters to closest primary reservoir.
        *   `population_served` (Integer, Required): Count of municipal consumers served by this pipeline segment.
        *   `upstream_node` (String, Required): Upstream connection node ID.
        *   `downstream_node` (String, Required): Downstream connection node ID.

### Example JSON Input Payload
```json
{
  "batch_id": "batch-2026-08-29-001",
  "timestamp": "2026-08-29T02:00:00Z",
  "telemetry_windows": [
    {
      "sensor_cluster_id": "cluster-desert-042",
      "network_metadata": {
        "signal_strength_dbm": -105,
        "packet_loss_pct": 12.5
      },
      "readings": [
        { "timestamp": "2026-08-29T01:51:00Z", "pressure_psi": 44.8, "flow_rate_lps": 80.2, "ambient_temp_c": 50.1 },
        { "timestamp": "2026-08-29T01:52:00Z", "pressure_psi": 44.5, "flow_rate_lps": 80.5, "ambient_temp_c": 50.3 },
        { "timestamp": "2026-08-29T01:53:00Z", "pressure_psi": 44.2, "flow_rate_lps": 80.1, "ambient_temp_c": 50.6 },
        { "timestamp": "2026-08-29T01:54:00Z", "pressure_psi": 44.0, "flow_rate_lps": 80.9, "ambient_temp_c": 50.9 },
        { "timestamp": "2026-08-29T01:55:00Z", "pressure_psi": 43.8, "flow_rate_lps": 81.1, "ambient_temp_c": 51.1 },
        { "timestamp": "2026-08-29T01:56:00Z", "pressure_psi": 43.1, "flow_rate_lps": 81.5, "ambient_temp_c": 51.3 },
        { "timestamp": "2026-08-29T01:57:00Z", "pressure_psi": 38.5, "flow_rate_lps": 95.2, "ambient_temp_c": 51.5 },
        { "timestamp": "2026-08-29T01:58:00Z", "pressure_psi": 32.4, "flow_rate_lps": 105.8, "ambient_temp_c": 51.6 },
        { "timestamp": "2026-08-29T01:59:00Z", "pressure_psi": 28.4, "flow_rate_lps": 112.5, "ambient_temp_c": 51.5 }
      ]
    },
    {
      "sensor_cluster_id": "cluster-desert-043",
      "network_metadata": {
        "signal_strength_dbm": -72,
        "packet_loss_pct": 0.0
      },
      "readings": [
        { "timestamp": "2026-08-29T01:55:00Z", "pressure_psi": 45.1, "flow_rate_lps": 75.0, "ambient_temp_c": 51.0 },
        { "timestamp": "2026-08-29T01:56:00Z", "pressure_psi": 45.0, "flow_rate_lps": 75.1, "ambient_temp_c": 51.2 },
        { "timestamp": "2026-08-29T01:57:00Z", "pressure_psi": 45.1, "flow_rate_lps": 75.0, "ambient_temp_c": 51.3 },
        { "timestamp": "2026-08-29T01:58:00Z", "pressure_psi": 44.9, "flow_rate_lps": 75.2, "ambient_temp_c": 51.5 },
        { "timestamp": "2026-08-29T01:59:00Z", "pressure_psi": 45.0, "flow_rate_lps": 75.1, "ambient_temp_c": 51.4 }
      ]
    }
  ],
  "pipeline_topology": {
    "segments": [
      {
        "segment_id": "seg-neom-north-01",
        "sensor_cluster_id": "cluster-desert-042",
        "associated_valve_id": "valve-neom-north-01",
        "criticality_score": 3,
        "proximity_to_reservoir_m": 120.0,
        "population_served": 45000,
        "upstream_node": "reservoir-main-north",
        "downstream_node": "blending-station-01"
      },
      {
        "segment_id": "seg-neom-north-02",
        "sensor_cluster_id": "cluster-desert-043",
        "associated_valve_id": "valve-neom-north-02",
        "criticality_score": 1,
        "proximity_to_reservoir_m": 4500.0,
        "population_served": 150,
        "upstream_node": "blending-station-01",
        "downstream_node": "agricultural-valve-04"
      }
    ]
  }
}
```

---

## 4. Anomaly Detection vs. Anomaly Investigation Logic

A core innovation of this updated spec is the explicit boundary and operational division between high-speed **Anomaly Detection** and context-aware **Anomaly Investigation**.

### Operational Division
*   **Anomaly Detection (Deterministic & Statistical filtering):** Low-cost, fast execution. Answers a binary question: *"Does this telemetry series deviate from expected healthy behavior?"* It runs continuously across all system logs.
*   **Anomaly Investigation (Agentic & Multi-signal Reasoning):** High-intelligence, deeper execution. Answers complex contextual questions: *"Why did this deviation occur? Is it a physical pipe burst, or did the hot desert sun overheat the cellular transceiver? What is the localized hydraulic impact and security implication?"* It runs selectively on suspicious detections only.

```
+───────────────────────────────────────────────────────────────────────────────────────────+
│                                  Stage Separation Matrix                                  │
+───────────────────────────────────────────────────────────────────────────────────────────+
│ Feature                Anomaly Detection Stage            Anomaly Investigation Stage     │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│ Target Scope           100% of incoming system logs       Suspicious/anomalous logs only  │
│ Primary Technology     Python, LSTM, Statistical Z-Scores   LangGraph Orchestrator + LLM  │
│ Network Dependencies   None (local DB reads/writes)       Nokia NaC CAMARA APIs           │
│ Computational Cost     Extremely Low (Sub-millisecond)    Medium (1-2s API/Inference)     │
│ Actionable Outcome     Flags normal vs. suspicious logs   Assigns Risk Tiers, alerts NMA  │
+───────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 5. Algorithmic Detail: Detection, Investigation, & Risk

### A. Anomaly Detection Algorithmic Layer
For each sensor cluster in the incoming batch, the AIA evaluates its trailing reading array:

1.  **Statistical Z-Score Check (Rate of Change):**
    For pressure ($P$) and flow ($Q$), the agent evaluates the standard deviation of the current reading against the historical baseline mean:
    
    $$Z_P = \frac{P_{\text{current}} - \mu_{P\_baseline}}{\sigma_{P\_baseline}}$$
    
    $$Z_Q = \frac{Q_{\text{current}} - \mu_{Q\_baseline}}{\sigma_{Q\_baseline}}$$
    
    If $|Z_P| \ge 3.0$ or $|Z_Q| \ge 3.0$, the cluster is flagged as `suspicious`.

2.  **Machine Learning Sequence Model (LSTM Autoencoder Integration):**
    To detect multi-signal and slow-developing anomalies, an LSTM Autoencoder model (pre-trained on historical seasonal pipeline pressures, flow rates, and ambient temperatures) evaluates the sequence of the last 10 readings:
    
    $$\mathbf{X} = \{x_{t-9}, x_{t-8}, \dots, x_{t}\}$$
    
    Where $x_t = [P_t, Q_t, T_{\text{ambient\_t}}]$.
    The model reconstructs the sequence:
    
    $$\mathbf{\hat{X}} = \text{LSTM\_Autoencoder}(\mathbf{X})$$
    
    The Mean Squared Error (MSE) reconstruction loss is calculated:
    
    $$\text{Loss}_{\text{MSE}} = \frac{1}{10}\sum_{i=1}^{10} (x_i - \hat{x}_i)^2$$
    
    *   If $\text{Loss}_{\text{MSE}} > \tau_{\text{threshold}}$ (where $\tau$ is a dynamic threshold scaled linearly by ambient temperature to account for thermal noise), the sequence is immediately classified as `suspicious` and promoted to Anomaly Investigation.
    *   If a cluster passes both Z-score and ML thresholds (e.g., `cluster-desert-043` in the input example), it is written directly to TimescaleDB as `normal` and bypassed.

---

### B. Anomaly Investigation Layer (Network vs. Asset Disambiguation)
When a sequence is flagged as `suspicious`, the agent initiates context-aware investigation using Nokia NaC CAMARA APIs to perform active hardware diagnostics.

```
                              [Suspicious Telemetry Sequence]
                                             │
                                             ▼
                             [Query CAMARA Device Status]
                                             │
                   ┌─────────────────────────┴─────────────────────────┐
                   ▼ (Online)                                          ▼ (Offline/Degraded)
         [Device Reachability API]                           [Query Temp & History]
                   │                                                   │
         ┌─────────┴─────────┐                           ┌─────────────┴─────────────┐
         ▼ (Reachable)       ▼ (Unreachable)             ▼ (Temp > 50°C)             ▼ (Temp < 50°C)
  [CONFIRMED ANOMALY]      [INSUFFICIENT DATA]         [LIKELY CELL FAILURE]       [CONFIRMED ANOMALY]
   (Physical Leak /         (Temporary signal           (Thermal degradation;       (Sensor hardware
   Pipe Rupture)             dropout/multipath)          ignore leak alert)          malfunction/power)
         │
         ▼
  [Risk Assessment]
```

1.  **CAMARA Device Status Check:** The agent retrieves real-time connection status:
    *   `camara_device_status == "disconnected"`: The agent inspects `ambient_temp_c`. If temperature $\ge 50^\circ\text{C}$ and historical connection charts show localized thermal cellular degradation, it classifies the event as `likely_connectivity_artifact`.
2.  **CAMARA Device Reachability Check:** If status is `connected`, the agent queries device reachability:
    *   `camara_reachability_status == "unreachable"`: Flagged as `insufficient_data`. The AIA triggers a localized, low-risk request to edge gateways to increase polling rates while ignoring automatic shutoff alerts.
    *   `camara_reachability_status == "reachable"`: The pipeline hardware is fully communicative. The anomaly is classified as a `confirmed_anomaly`.

---

### C. Risk Assessment & Severity Tiering
For every `confirmed_anomaly`, the agent assesses physical severity and network risk based on hydraulic trends and the pipeline topology:

1.  **Trend Deviation Calculation:**
    Using the last 10 readings, the agent calculates the percent deviation from baseline and the velocity slope ($m$) using simple linear regression:
    
    $$\Delta P\% = \frac{P_{\text{baseline}} - P_{\text{current}}}{P_{\text{baseline}}} \times 100$$
    
    $$\Delta Q\% = \frac{Q_{\text{current}} - Q_{\text{baseline}}}{Q_{\text{baseline}}} \times 100$$
    
    $$m_P = \frac{10\sum(t \cdot P_t) - \sum t\sum P_t}{10\sum t^2 - (\sum t)^2}$$

2.  **Risk Matrix Evaluation:**
    Using the segment criticality metadata ($C$, scale 1-3) parsed from the `pipeline_topology` payload, the agent maps severity:
    *   **Tier 1 (Minor / Monitor Only):** $\Delta P < 15\%$, $\Delta Q < 20\%$, and $C \le 1$.
        *   *Root Cause:* Slow structural pinhole leak or instrument drift.
        *   *Downstream Action:* Silent dashboard log.
    *   **Tier 2 (Moderate / Escalation Required):** $15\% \le \Delta P < 35\%$ OR $C = 2$.
        *   *Root Cause:* Growing pipeline crack or auxiliary line leak.
        *   *Downstream Action:* Boost network connectivity priority (CAMARA QoD) to guarantee live streaming, alert human operators, and request manual field validation.
    *   **Tier 3 (Catastrophic / Autonomous Action):** $\Delta P \ge 35\%$, $m_P < -2.0$ (steep, rapid decay), and $C = 3$.
        *   *Root Cause:* Major physical pipeline burst near crucial assets (e.g., NEOM residential reservoirs).
        *   *Downstream Action:* Request dedicated network slice, dispatch emergency SMS, and command immediate autonomous closure of the downstream motorized isolation valve.

---

## 6. AI/LLM Architecture

The technical design of the AIA relies on an agentic orchestration layer powered by LangGraph, wrapping external database operations and CAMARA APIs through Model Context Protocol (MCP) servers.

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
│  │  - get_reachability()     - get_topology()       │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Deterministic vs. Heuristic (LLM) Boundary
*   **Deterministic Logic (Python execution):** Raw statistical calculation ($Z$-scores), ML Autoencoder scoring, dynamic CAMARA API network wrappers, and hardcoded safety limit enforcements (e.g., forcing a Tier 3 if pressure drops $\ge 50\%$ on highly critical lines). This guarantees safety and eliminates LLM hallucination risks.
*   **Agentic/LLM Reasoning (GPT-4o or Claude 3.5 Sonnet):** Initiated *only* for suspicious logs. The LLM processes the aggregated outputs (network status, historical heat patterns, hydraulic trends) to identify complex anomalies (such as a slow, thermal-induced pipe leak hiding under network congestion), synthesize the plain-language Operator Justification Memo, and output the final validated JSON.

### Context & Memory Management
The agent maintains an active state graph of the active batch. To preserve rapid execution and avoid high token overhead, the agent does not use vector-store RAG. Instead, it maintains a short-term sliding context containing:
1.  The windowed telemetry sequence of the suspicious sensor cluster.
2.  The structural topology metadata associated with that cluster’s segment.
3.  The real-time responses returned from the CAMARA API tools.

### Guardrails & Safety
*   **The Actuator Isolation Guardrail:** The AIA is structurally prohibited from triggering motorized valve actuators directly. Physical action commands are reserved exclusively for the downstream **Network Management Agent** after evaluation.
*   **Schema Enforcement:** LangChain Pydantic output parsers validate LLM outputs against the strict schema before serialization.
*   **API Cost Capping:** To prevent runaway loops, Nokia CAMARA tool executions are subject to strict rate limits (maximum 1 request per sensor cluster per 5-minute interval).

---

## 7. Output Specification

The AIA produces a strictly validated JSON payload representing the **batch investigation report**. It contains detailed diagnostics for **only suspicious or verified anomalous clusters**, completely filtering out healthy operational telemetry.

### Structured Output JSON Schema (Pydantic v2 format)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AIA_Batch_Output_Payload",
  "type": "object",
  "properties": {
    "batch_id": { "type": "string" },
    "analysis_timestamp": { "type": "string", "format": "date-time" },
    "total_clusters_analyzed": { "type": "integer" },
    "anomalies_detected_count": { "type": "integer" },
    "investigated_threats": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "anomaly_id": { "type": "string", "format": "uuid" },
          "sensor_cluster_id": { "type": "string" },
          "segment_id": { "type": "string" },
          "classification": { 
            "type": "string", 
            "enum": ["confirmed_anomaly", "likely_connectivity_artifact", "insufficient_data"] 
          },
          "severity_tier": { "type": "integer", "enum": [1, 2, 3] },
          "network_status": {
            "type": "object",
            "properties": {
              "device_online": { "type": "boolean" },
              "device_reachable": { "type": "boolean" },
              "network_degradation_detected": { "type": "boolean" },
              "camara_device_status": { "type": "string" },
              "camara_reachability_status": { "type": "string" }
            },
            "required": ["device_online", "device_reachable", "network_degradation_detected"]
          },
          "physical_deviations": {
            "type": "object",
            "properties": {
              "pressure_drop_pct": { "type": "number" },
              "flow_surge_pct": { "type": "number" },
              "pressure_slope": { "type": "number" },
              "flow_slope": { "type": "number" }
            },
            "required": ["pressure_drop_pct", "flow_surge_pct"]
          },
          "criticality_metrics": {
            "type": "object",
            "properties": {
              "criticality_score": { "type": "integer", "minimum": 1, "maximum": 3 },
              "proximity_to_reservoir_m": { "type": "number" },
              "population_served": { "type": "integer" },
              "associated_valve_id": { "type": "string" }
            },
            "required": ["criticality_score", "proximity_to_reservoir_m", "population_served", "associated_valve_id"]
          },
          "operator_justification": { "type": "string" },
          "confidence_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
        },
        "required": [
          "anomaly_id", "sensor_cluster_id", "segment_id", "classification", 
          "severity_tier", "network_status", "physical_deviations", 
          "criticality_metrics", "operator_justification", "confidence_score"
        ]
      }
    }
  },
  "required": [
    "batch_id", "analysis_timestamp", "total_clusters_analyzed", "anomalies_detected_count", "investigated_threats"
  ]
}
```

### Example JSON Output Payload
This example shows the processed output corresponding to the input payload in Section 3. Note that `cluster-desert-043` has been correctly filtered out of the report as `normal` by Stage 1, leaving only the verified high-risk threat at `cluster-desert-042` to minimize downstream network and agent resource consumption.
```json
{
  "batch_id": "batch-2026-08-29-001",
  "analysis_timestamp": "2026-08-29T02:00:03Z",
  "total_clusters_analyzed": 2,
  "anomalies_detected_count": 1,
  "investigated_threats": [
    {
      "anomaly_id": "987234da-c42a-43df-b423-5e783451ab02",
      "sensor_cluster_id": "cluster-desert-042",
      "segment_id": "seg-neom-north-01",
      "classification": "confirmed_anomaly",
      "severity_tier": 3,
      "network_status": {
        "device_online": true,
        "device_reachable": true,
        "network_degradation_detected": false,
        "camara_device_status": "CONNECTED",
        "camara_reachability_status": "REACHABLE"
      },
      "physical_deviations": {
        "pressure_drop_pct": 36.6,
        "flow_surge_pct": 40.6,
        "pressure_slope": -3.42,
        "flow_slope": 7.31
      },
      "criticality_metrics": {
        "criticality_score": 3,
        "proximity_to_reservoir_m": 120.0,
        "population_served": 45000,
        "associated_valve_id": "valve-neom-north-01"
      },
      "operator_justification": "A catastrophic pressure drop of 36.6% accompanied by a 40.6% flow rate spike was detected at cluster-desert-042, showing rapid progressive degradation (pressure slope -3.42 psi/min). The Nokia CAMARA APIs confirm the device is fully online and reachable with normal cellular performance. Because this segment is situated 120 meters from the primary northern reservoir and supplies water to 45,000 residents, this is investigated and confirmed as a catastrophic physical pipeline burst (Tier 3) requiring immediate closure of downstream valve valve-neom-north-01.",
      "confidence_score": 0.99
    }
  ]
}
```

---

## 8. Interface Between Agents

To prevent latency and network saturation, the agent communication protocol is asynchronous and highly decoupled.

### Interface Data Flow
```
    Raw Bulk Logs (AIA Input)
              │
              ▼
  ┌───────────────────────┐
  │ Anomaly Investigation │
  │      Agent (AIA)      │
  └───────────┬───────────┘
              │  Only suspicious/confirmed anomaly payloads (AIA Output)
              ▼
  ┌───────────────────────┐
  │  Network Management   │
  │      Agent (NMA)      │
  └───────────┬───────────┘
              │  Autonomous/Triggered Network or Mechanical Actions
              ▼
  [Nokia CAMARA QoD / Slicing API]  ──►  [Valve Actuator Command]
```

### Data Handoff and Interpretation Rules
1.  **Strict Payload Separation:** Raw pressure log arrays are kept in TimescaleDB. Only the processed `AIA_Batch_Output_Payload` is transmitted across agents. This reduces memory overhead and decouples the analysis layer from the orchestration execution.
2.  **Downstream Interpretation:**
    *   `classification == "likely_connectivity_artifact"`: The Network Management Agent (NMA) will bypass any leak alerts, log the incident as a cellular/gateway issue, and schedule a routine telemetry-maintenance ticket.
    *   `severity_tier == 2`: The NMA triggers an immediate **Quality on Demand (QoD) API** priority boost to guarantee continued high-frequency reporting, and sends an SMS/email alert to human field teams.
    *   `severity_tier == 3`: The NMA immediately requests a **Dedicated Network Slice** (covering the sensor corridor and the valve actuator), fires an autonomous isolation command to the motorized valve, and alerts operators.
3.  **Uncertainty & Error Handling:**
    *   If `confidence_score` $< 0.70$ or `classification == "insufficient_data"`, the NMA defaults to a protective fallback state: it triggers a temporary QoD priority boost to stabilize data flow, and immediately requests human operator confirmation rather than taking autonomous physical actions.
    *   If the AIA experiences an internal crash or LLM timeout, a hard-coded fallback event handler generates a default payload of `severity_tier: 2` with a `system_error` flag, forcing human-in-the-loop escalation.

---

## 9. Implementation Roadmap & Testing Plan

This roadmap provides a phased engineering plan for the MVP.

### Phase 1: Environment Setup & Mock Integration
*   Deploy LangGraph orchestrator container and setup TimescaleDB schemas.
*   Create mockup interfaces for the Nokia NaC endpoints using FastAPIs:
    *   `GET /camara/device-status/v1` -> returns simulated signal health.
    *   `GET /camara/device-reachability/v1` -> returns reachability status.

### Phase 2: Agent Logic & Tool Development
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

### Phase 3: Validation, Testing & Evaluation
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
