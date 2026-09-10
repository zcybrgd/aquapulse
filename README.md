# AquaPulse: Autonomous Smart Water Intelligence & Network Resilience Platform

AquaPulse is an autonomous, end-to-end smart water management and wireless network resilience platform engineered for critical infrastructure in extreme and arid environments (e.g., MENA/NEOM, desert terrains with ambient temperatures exceeding 50°C).

Smart water infrastructures face a dual threat: physical pipeline bursts waste precious desalinated water, while high temperatures degrade cellular IoT connectivity, delaying or dropping emergency telemetry. AquaPulse addresses this by unifying autonomous AI agent orchestration, telecom-grade network resource management via Nokia Network-as-Code (NaC) CAMARA APIs, real-time spatial analytics, and closed-loop emergency valve actuation.

---

## 1. High-Level Architecture & End-to-End Workflow

AquaPulse coordinates four core operational layers: raw telemetry ingestion and disambiguation, dynamic 5G cellular prioritization, safety-critical response execution, and real-time operator control.

```mermaid
flowchart TD
    subgraph Testbed ["Water Pipeline Testbed / Edge Telemetry"]
        TB[Sensors: Pressure, Flow Rate, Ambient Temp]
    end

    subgraph AIA ["1. Anomaly Investigation Agent (AIA)"]
        A1[Raw Telemetry Ingestion] --> A2{Dual-Layer Detection\nZ-Score & Isolation Forest}
        A2 -- Normal --> DB1[(TimescaleDB Archive)]
        A2 -- Suspicious --> A3[CAMARA API Disambiguation\nReachability & Congestion]
        A3 --> A4[Deterministic Risk & Hydraulic Slope Matrix\nTier 1 / Tier 2 / Tier 3]
        A4 --> A5[LLM Narration Node\nOperator Justification Memo]
    end

    subgraph NMA ["2. Network Management Agent (NMA)"]
        N1[Batch Ingestion & Severity/Criticality Ranking] --> N2[Regional Cluster/Zone Grouping]
        N2 --> N3{LLM Network Policy Engine}
        N3 -- Tier 2 Priority Boost --> N4[CAMARA QoD Session]
        N3 -- Tier 3 Rupture --> N5[5G Network Slice Attachment]
        N3 -- Unreachable/Routine --> N6[Direct Denial / Best Effort / SMS Fallback]
    end

    subgraph RA ["3. Response Agent (RA)"]
        R1[Live Pre-Actuation Reachability Check] --> R2{LLM Planner & Deterministic Guardrail}
        R2 -- Tier 1: Log Only --> R3[Audit Logging]
        R2 -- Tier 2: Alert & Await --> R4[Notification Service - SMS Dispatch]
        R2 -- Tier 3: Autonomous Isolate --> R5[Valve Actuator Service - Motorized Isolation]
        R5 --> R6[Bounded Human Override Window]
        R6 --> R7[(Immutable JSONL Audit Sink)]
    end

    subgraph Platform ["4. AquaPulse Operational Control Platform"]
        P1[FastAPI Backend - Port 8000] <--> P2[TimescaleDB + PostGIS]
        P1 <--> P3[React 18 Dashboard - Port 5173]
    end

    TB --> AIA
    AIA -- "Investigated Threats Payload" --> NMA
    NMA -- "Async Grant/Denial Dispatches" --> RA
    AIA & NMA & RA --> Platform

```

---

## 2. Core Platform Components

### 2.1 Anomaly Investigation Agent (AIA)

Located in `agents/`, the AIA serves as the diagnostic brain of AquaPulse. It consumes high-frequency telemetry streams and isolates true physical bursts from cellular network dropouts under extreme environmental heat.

* **Stage 1: Dual-Layer Anomaly Detection:**
* *Deterministic Safety Floor:* Flags instant pressure drops ($\ge 15\%$) or flow surges ($\ge 20\%$) using rolling $Z$-score evaluations ($\vert{}Z_P\vert{} \ge 3.0$ or $\vert{}Z_Q\vert{} \ge 3.0$).
* *Bootstrap Isolation Forest:* Uses a temperature-adaptive machine learning model trained on baseline window readings to identify subtle, multi-variable hydraulic drifts.


* **Stage 2: CAMARA Disambiguation (Network vs. Asset Diagnostics):**
* Queries Nokia CAMARA **Device Reachability Status** and **Congestion Insights** APIs.
* *Disambiguation Matrix:*
* Device **REACHABLE** + Hydraulic Anomaly = `confirmed_anomaly`
* Device **UNREACHABLE** + High Sector Congestion + Temp $\ge 50^\circ\text{C}$ = `likely_connectivity_artifact` (thermal cell degradation)
* Device **UNREACHABLE** + Low Congestion = `confirmed_instrument_fault` (sensor blowout / power cut)
* API Error / Socket Timeout = `insufficient_data` (triggers retry and operator escalation)




* **Stage 3: Deterministic Risk Tiering & Metrics:**
* Calculates hydraulic pressure slope ($m_P$) and flow slope ($m_Q$) over trailing windows using linear regression.
* Assigns actionable severity tiers (Tier 1, Tier 2, Tier 3) based on pressure drop magnitude ($\Delta P\%$), hydraulic slope, and pipeline segment criticality score ($C \in [1, 3]$).
* Computes a mathematical `confidence_score` ($0.0 \text{ to } 1.0$) combining telemetry completeness ($40\%$), CAMARA reliability ($40\%$), and trend linearity ($20\%$).


* **Stage 4: Read-Only LLM Narration:**
* Prompts an LLM (Claude/Groq) strictly as a read-only narrator to write concise "Operator Justification Memos". The LLM is prohibited from altering tiers, classifications, or numerical scores computed by Python.



---

### 2.2 Network Management Agent (NMA)

Located in `agents/network_agent/`, the NMA dynamically manages cellular bandwidth allocations to ensure telemetry and emergency commands survive network congestion during critical incidents.

* **Ingestion, Ranking & Grouping:**
* Consumes investigation batches from Redis channel `aia:results`.
* Ranks actionable requests in descending order by `severity_tier` $\rightarrow$ `criticality_score` $\rightarrow$ `confidence_score`.
* Groups requests regionally by `sensor_cluster_id` or `zone_id`.


* **LLM Decision Policy Engine:**
* Powered by `ChatGroq` (`openai/gpt-oss-120b` or `llama-3.3-70b-versatile`, temperature `0`).
* Allocates **5G Network Slicing** (`PREPROVISIONED_SLICE_ID`) for Tier 3 sustained ruptures or multi-device corridor isolations.
* Allocates **CAMARA Quality on Demand (QoD)** priority sessions for single-device rapid requests (Tier 2).
* Refuses allocations to offline/unreachable devices and emits `SMS` fallbacks.


* **Response Agent Bridge & Release API:**
* Dispatches grants and denials directly to the Response Agent via background thread pools without blocking network orchestrator loops.
* Exposes an HTTP release server (`agents/network_agent/release_server.py` on port `8000`) providing `POST /v1/qod/release` and `POST /v1/slice/release` endpoints.



---

### 2.3 Response Agent (RA)

Located in `agents/response_agent/`, the RA handles high-stakes, safety-critical reaction logic using a structured LangGraph state graph.

```
[Incident Event] ──► [reachability_check] ──► [llm_response_planner] ──► [execute_response] ──► [human_override] ──► [audit_writer] ──► END

```

* **Node Breakdown:**
1. `reachability_check`: Queries `DeviceReachabilityClient` immediately before command execution. Fails closed (`reachable=False`) on any network failure or timeout to prevent blind actuation.
2. `llm_response_planner`: Prompts an LLM to generate an operator notification message, then forces the decision through a strict deterministic Python guardrail (`_enforce_guardrails`). The guardrail overrides any hallucinated LLM decision.
3. `execute_response`: Branches on decision state:
* `LOG_ONLY`: Quiet audit log.
* `ALERT_AND_AWAIT` / `ESCALATE_UNREACHABLE`: Dispatches operator SMS via `NotificationClient`.
* `AUTONOMOUS_ISOLATE`: Sends an urgent SMS and executes motorized valve shutoff via `ValveActuatorClient`. Raises `ValveCommandError` on non-confirmation.


4. `human_override`: Opens a bounded time window (`override_window_seconds`) for operators to confirm or override autonomous isolations. Times out safely if unacknowledged.
5. `audit_writer`: Appends immutable `AuditLogEntry` JSON records to `audit_log.jsonl`.



---

### 2.4 AquaPulse Control Platform (`plateform/`)

The operational UI and data persistence engine built with FastAPI, PostgreSQL 16, TimescaleDB, PostGIS, and React 18.

* **TimescaleDB & PostGIS Integration:** Stores continuous 5-minute sensor telemetry in a hypertable (`sensor_readings`) while managing geospatial vector layers for pipelines, valves, reservoirs, and sensor nodes.
* **Core Modules:**
* **Overview & Map Dashboard:** Real-time KPIs, PostGIS live network map, active incident counters, and hydraulic pressure distribution.
* **Incident & Operations Center:** Operator workflows for acknowledging, assigning, investigating, approving, and resolving incidents.
* **Maintenance Center:** Schedules corrective/preventive work orders (`MWO-xxxxxx`) linked to assets and incidents.
* **Device Network Health:** Direct Nokia NaC / CAMARA API status, reachability metrics, and masked MSISDN identity inspection.



---

### 2.5 Microservices Ecosystem

| Microservice Directory | Default Port | Description |
| --- | --- | --- |
| `camara-integration/src` | `8001` | CAMARA API adapter simulating/wrapping Nokia Device Reachability, Location Retrieval, and QoD Session management. |
| `notification-service` | `8002` | REST SMS and broadcast dispatch service used by the Response Agent. |
| `valve-actuator-sim` | `8003` | Actuator simulation service exposing `POST /v1/valve/isolate` for physical valve closure testing. |
| `water-pipeline-testbed` | `8080` | Telemetry generator producing streaming pressure, flow rate, and ambient temperature readings. |

---

## 3. Directory & Repository Structure

```text
aquapulse/
├── AGENT INTEGRATION.md           # Integration readiness and adapter contracts
├── audit_log.jsonl                # Immutable append-only audit trail
├── requirements.txt               # Master Python dependency manifest
├── run.sh                         # Master orchestrator startup script
├── agents/                        # Autonomous Agent Source Directory
│   ├── network_agent/             # Network Management Agent (NMA)
│   │   ├── runner.py              # Listener & pre-provisioned slice initializer
│   │   ├── release_server.py      # HTTP release API (QoD/Slice teardown)
│   │   ├── tools.py               # CAMARA QoD, Slicing, and Congestion tools
│   │   └── policy.py              # System prompts & LLM allocation policies
│   ├── response_agent/            # Response Agent (RA)
│   │   ├── main.py                # Scenario runner CLI
│   │   ├── graph.py               # LangGraph 5-node actuation pipeline
│   │   ├── schemas.py             # Pydantic v2 schemas (SeverityTier, AuditLogEntry)
│   │   ├── llm_response_planner.py# LLM planner & guardrail implementation
│   │   ├── reachability_check.py  # Fail-closed reachability check node
│   │   ├── execute_response.py    # Notification & physical valve actuation execution
│   │   ├── human_override.py      # Bounded human approval / override handler
│   │   └── audit_writer.py        # Append-only JSONL audit sink
│   └── anomaly_investigation_agent/ # Anomaly Investigation Agent (AIA)
│       ├── detection.py           # Z-Score & Isolation Forest detection logic
│       ├── investigation.py       # CAMARA disambiguation & hydraulic slope math
│       └── narrator.py            # Read-only LLM memo generation
├── camara-integration/            # Nokia NaC / CAMARA Integration Service (Port 8001)
├── notification-service/          # SMS Dispatch Microservice (Port 8002)
├── valve-actuator-sim/            # Motorized Valve Actuator Simulator (Port 8003)
├── water-pipeline-testbed/        # Synthetic Telemetry Generator / Testbed
└── plateform/                     # AquaPulse Full-Stack Platform
    ├── docker-compose.yml         # PostgreSQL 16 (TimescaleDB + PostGIS) container setup
    ├── backend/                   # FastAPI Backend Application
    │   ├── alembic/               # Database migrations (0001 through 0011_network_audit)
    │   └── app/                   # API routes, services, and seeding scripts
    └── frontend/                  # React 18 + Vite + Tailwind CSS User Interface

```

---

## 4. Actionable Risk Tiers & System Policies

| Risk Tier | Criteria / Trigger | AIA Classification | NMA Strategy | Response Agent Action |
| --- | --- | --- | --- | --- |
| **Tier 1 (Monitor)** | $\Delta P\% < 15\%$, low criticality ($C=1$). Minor pinhole leak or sensor drift. | `confirmed_anomaly` | Direct Denial / Best Effort | Logged silently to database and audit sink (`LOG_ONLY`). No human alert. |
| **Tier 2 (Alert)** | $15\% \le \Delta P\% < 35\%$ or segment criticality $C=2$. Progressive crack. | `confirmed_anomaly` | CAMARA Quality on Demand (QoD) | SMS alert dispatched to regional field operator (`ALERT_AND_AWAIT`). Awaits human confirmation. |
| **Tier 3 (Catastrophic)** | $\Delta P\% \ge 35\%$, $m_P < -2.0$ psi/min, criticality $C=3$. Major rupture near main reservoir. | `confirmed_anomaly` | 5G Network Slice Attachment | Immediate autonomous motorized valve isolation (`AUTONOMOUS_ISOLATE`) + simultaneous SMS + bounded human override window. |
| **Instrument Fault** | Instant flatline telemetry, device `UNREACHABLE`, low sector congestion. | `confirmed_instrument_fault` | Direct Denial / Best Effort | Bypasses physical valve loops entirely. Dispatches maintenance field ticket (`MWO-xxxxxx`). Telemetry marked stale. |
| **Cell Degradation** | Device `UNREACHABLE`, high cell congestion, ambient temp $\ge 50^\circ\text{C}$. | `likely_connectivity_artifact` | Direct Denial / Best Effort | Suppresses physical leak alarms. Logs low-urgency cell thermal degradation event. |
| **Network Blindness** | CAMARA API socket error / platform timeout. | `insufficient_data` | Conservative QoD Boost | Escalates to human operator console for manual validation. Retries investigation in next cycle. |

---

## 5. Environment Variables & Configuration

Set up environment files before running the application:

### Platform Backend (`plateform/backend/.env`)

```ini
POSTGRES_DB=aquapulse
POSTGRES_USER=aquapulse
POSTGRES_PASSWORD=aquapulse
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse
TEST_DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse_test
TELEMETRY_SIMULATOR_ENABLED=false
NOKIA_NETWORK_API_ENABLED=false
NOKIA_NETWORK_API_MODE=mock

```

### Anomaly Investigation Agent (`agents/investigation_agent/.env`)

```ini
RAPIDAPI_KEY=your_nokia_NaC_key
RAPIDAPI_HOST=network-as-code.nokia.rapidapi.com
GROQ_API_KEY=your_groq_api_key
REDIS_URL="redis://127.0.0.1:6380/0"

```

### Root Directory (`.env`)

```ini
RAPIDAPI_HOST="network-as-code.nokia.rapidapi.com"
RAPIDAPI_KEY=your_nokia_NaC_key
GROQ_API_KEY=your_groq_api_key
RESPONSE_AGENT_MODEL="openai/gpt-oss-20b"
GROQ_MODEL= "openai/gpt-oss-20b"
WEBHOOK_URL=your_webhook_url
CONGESTION_NOTIFICATION_URL = "https://example.com/notifications"
CONGESTION_NOTIFICATION_AUTH_TOKEN = your_congestion_notification_auth_token
REDIS_HOST="localhost"
REDIS_PORT=6380

```

---

## 6. Installation & Quick Start Guide

### 6.1 Prerequisites

* Python 3.11 or newer
* Node.js 20+ and npm 10+
* Docker Desktop (or Docker Engine with Compose v2)
* Redis Server (`localhost:6379`)

---

### 6.2 Running the Supporting Microservices

Start the three mock dependency microservices in separate terminal windows:

```bash
# Terminal 1: Nokia CAMARA Integration Service (Port 8001)
python -m uvicorn main:app --app-dir camara-integration/src --port 8001 --host 127.0.0.1

# Terminal 2: Notification Service (Port 8002)
python -m uvicorn main:app --app-dir notification-service --port 8002 --host 127.0.0.1

# Terminal 3: Valve Actuator Simulator (Port 8003)
python -m uvicorn main:app --app-dir valve-actuator-sim --port 8003 --host 127.0.0.1

```

---

### 6.3 Running the AquaPulse Platform

1. **Start Database Services:**
```bash
cd plateform
docker compose up -d

```


Wait until container `aquapulse-db` is healthy (`docker compose ps`).
2. **Initialize Backend Environment & Database:**
```bash
cd plateform/backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Apply Alembic Migrations
alembic upgrade head

# Seed Demonstration Data (Assets, Zones, Historical Readings, Incidents)
python -m app.scripts.seed_database

```


3. **Start Platform API Server:**
```bash
# From plateform/backend with .venv active:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

```


* REST API Docs: [http://127.0.0.1:8000/docs](https://www.google.com/search?q=http://127.0.0.1:8000/docs)
* API Health Check: [http://127.0.0.1:8000/api/health](https://www.google.com/search?q=http://127.0.0.1:8000/api/health)


4. **Start Frontend User Interface:**
```bash
cd plateform/frontend
npm install
npm run dev

```


Access the dashboard at [http://127.0.0.1:5173](https://www.google.com/search?q=http://127.0.0.1:5173).

---

### 6.4 One-Touch Launch Script (`run.sh`)

You can launch the entire stack (Database, Backend, Frontend, Microservices, and Agents) using the provided shell script from the repository root:

```bash
chmod +x run.sh
./run.sh

```

---

## 7. Scenario Testing & Verification

The Response Agent includes built-in scenario runners to test system safety policies under various conditions.

Run scenarios directly from the root environment:

```bash
# 1. Tier 1 Monitoring Scenario (Log Only)
python -m agents.response_agent.main --scenario tier1

# 2. Tier 2 Priority Alert Scenario (SMS Dispatch)
python -m agents.response_agent.main --scenario tier2

# 3. Tier 3 Catastrophic Rupture Scenario (Autonomous Valve Isolation)
python -m agents.response_agent.main --scenario tier3

# 4. Device Unreachable Scenario (Guardrail forces ESCALATE_UNREACHABLE over Tier 3)
python -m agents.response_agent.main --scenario unreachable

# 5. Actuator Command Failure Scenario (Triggers emergency escalation SMS)
python -m agents.response_agent.main --scenario actuator_failure

```

### Verification Expected Output Example (`--scenario tier3`)

```text
================================================================================
AQUAPULSE RESPONSE AGENT — SCENARIO RUNNER
Scenario: tier3
================================================================================
[reachability_check] Device device-14-valve-A is REACHABLE (Signal: RSRP -82 dBm, Good)
[llm_response_planner] LLM proposed decision: AUTONOMOUS_ISOLATE
[llm_response_planner] Guardrails verified: AUTONOMOUS_ISOLATE matches policy.
[execute_response] SMS notification sent to +971500000000.
[execute_response] VALVE ISOLATED: Actuator device-14-valve-A successfully closed for incident INC-TEST-TIER3.
[human_override] Operator window opened (300s). Response: CONFIRMED.
[audit_writer] Audit entry written to audit_log.jsonl.
--------------------------------------------------------------------------------
DECISION: AUTONOMOUS_ISOLATE
OPERATOR MESSAGE: EMERGENCY: Catastrophic rupture detected on segment-17. Valve device-14-valve-A autonomously isolated. Reply OVERRIDE to cancel.
================================================================================

```

---

## 8. Data Contracts & Schemas

### 8.1 Investigation Agent Output Schema (`AIA_Batch_Output_Payload`)

```json
{
  "batch_id": "batch-2026-08-31-001",
  "analysis_timestamp": "2026-08-31T02:00:03Z",
  "total_clusters_analyzed": 3,
  "anomalies_detected_count": 1,
  "investigated_threats": [
    {
      "anomaly_id": "987234da-c42a-43df-b423-5e783451ab02",
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
        "pressure_drop_pct": 36.6,
        "flow_surge_pct": 40.6,
        "pressure_slope": -3.42,
        "flow_slope": 7.31,
        "is_stale_pre_outage_data": false
      },
      "criticality_metrics": {
        "criticality_score": 3,
        "proximity_to_reservoir_m": 120.0,
        "population_served": 45000,
        "associated_valve_id": "valve-neom-north-01"
      },
      "operator_justification": "A catastrophic pressure drop of 36.6% with a 40.6% flow rate spike was detected at cluster-desert-042. CAMARA APIs confirm the device is reachable with low cell congestion. Confirmed as a physical pipeline rupture (Tier 3) requiring downstream valve isolation.",
      "confidence_score": 0.98
    }
  ]
}

```

### 8.2 Network Grant Event (`NetworkGrant`)

```json
{
  "status": "GRANTED",
  "decision": {
    "cluster_id": "cluster-desert-042",
    "incident_id": "987234da-c42a-43df-b423-5e783451ab02",
    "severity_tier": 3,
    "guarantee_type": "slice",
    "session_id": "slice-session-9921",
    "granted_at": "2026-08-31T02:00:04Z",
    "reasoning_trace": "Catastrophic rupture on high-criticality segment requires 5G network slice for guaranteed valve actuation payload.",
    "expires_at": "2026-08-31T03:00:04Z"
  }
}

```

---

## 9. Safety, Guardrails & Auditability

1. **Fail-Closed Reachability:** Physical valve commands are never issued without a live, successful reachability check immediately preceding actuation. If a device goes dark, the system downgrades execution to `ESCALATE_UNREACHABLE` and alerts human operators.
2. **Deterministic LLM Override Guardrails:** Language models are restricted to drafting messages and proposals. Plain Python guardrail logic (`_enforce_guardrails`) re-evaluates all decisions against deterministic tables. The LLM cannot override mathematical risk calculations or safety rules.
3. **Strict Parameter Validation:** All field identifiers (sensor IDs, cluster IDs) pass strict boundary regex validation (`^[a-zA-Z0-9\-]{1,64}$`) before prompt interpolation to eliminate prompt injection risks.
4. **Immutable Audit Trail:** All decisions, network grants, raw signal qualities, LLM reasoning traces, and human override outcomes are logged to `audit_log.jsonl` and persisted in PostgreSQL (`agent_audit_events`).