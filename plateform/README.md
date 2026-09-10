# AquaPulse

Operational control platform for water-network visibility.

This repository currently includes **Steps 1–12**:

- Step 1: project foundation, application shell, Overview dashboard
- Step 2: Incident Center, Incident Details, incident APIs
- Step 3: PostgreSQL persistence for incidents
- Step 4: read-only Asset Registry and Asset Details
- Step 5: PostGIS and the Live Network Map
- Step 6: TimescaleDB, persistent `sensor_readings`, historical seed, and a development telemetry simulator
- Step 7: deterministic anomaly detection, investigation queue, and a future agent-input contract
- Step 8: human investigation workflow and manual detection-to-incident promotion
- Step 9: Operations Center and human incident-response workflow
- Step 10: Analytics and performance insights over simulated telemetry and recorded operations
- Step 11: Agent Integration Readiness Gateway (contracts, adapters, mappings, mock services)
- Step 11.1: Device location, direct zone, and cellular identity (masked MSISDN)
- Maintenance Center (0010): plans, work orders, append-only history (present, not expanded in Step 12)
- Step 12: Unified Agent Audit Trail (historical Network Agent draft events remain stored)
- Device Network Health: backend Nokia Network as Code / CAMARA snapshots (not an agent)

Authentication, real IoT/SCADA ingestion, Kafka, WebSockets, live AI agent execution, automatic incident creation, real CAMARA APIs, valve actuation, notifications, and automatic background scheduling remain out of scope.

A **detection** is a suspicious telemetry pattern found by the lightweight screening model. It is **not** a confirmed incident and is **not** labelled as a leak. Authoritative pipeline:

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
| Candidate detection | Lightweight model |
| Confirmation, classification, confidence, severity | Investigation Agent |
| Connectivity, CAMARA, QoD | Network Management Agent |
| Response recommendation / action request | Response Agent |
| Persistence, UI, mapping, audit, safety | AquaPulse |

AquaPulse does **not** duplicate agent reasoning or decision rules. Existing deterministic detection is the lightweight screening model. Its priority is **Screening priority**, not final severity.

The detection engine is rule-based. It is not artificial intelligence.

Initial rule thresholds are **engineering demo values**. They require calibration with field data before operational use.

The development database image is `timescale/timescaledb-ha:pg16` (PostgreSQL 16 with TimescaleDB and PostGIS). Sensor telemetry is **simulated** and stored in TimescaleDB. Incident evidence in `incident_telemetry` is unchanged. Map geometry remains **seeded demonstration data**.

Asset management is **read-only**. There are no create, edit, delete, or command endpoints.

Development database credentials in Docker Compose and `.env.example` are **local defaults only**. Change them before any production deployment.

**To start the app on this machine, follow [How to run AquaPulse locally](#how-to-run-aquapulse-locally).** The numbered sections after that are reference detail (migrations, seeding, simulators, APIs).

## How to run AquaPulse locally

These are the only steps required to open the UI and talk to the API. They were verified on Windows 10 with Docker Desktop 27.2.0:

- `GET http://127.0.0.1:8000/api/health` returned `database: connected`, `postgis: available`, `timescaledb: available`
- `GET /api/dashboard/summary` returned live KPIs (`16` sensors, `7` active incidents)
- `GET /api/incidents` returned `9` incidents
- Frontend responded `200` at [http://127.0.0.1:5173](http://127.0.0.1:5173)

Work from `plateform/` (this folder: `aquapulse/plateform`). It has its own `docker-compose.yml`. Do not use the Compose file in the parent `aquapulse/` directory for this app. Keep **two terminals** open for the last two steps: one for the API, one for the UI.

```powershell
cd C:\doha_hackathon\aquapulse\plateform
```

### 1. Install prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm 10 or newer
- Docker Desktop (or another Docker Engine with Compose v2)

On Windows, start **Docker Desktop** and wait until this command succeeds (it can take a minute):

```powershell
docker info
```

If `docker compose` hangs or prints nothing, Docker Desktop is not ready yet.

### 2. Create environment files

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

macOS / Linux:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`frontend/.env` should keep:

```text
VITE_API_URL=http://localhost:8000
```

`backend/.env` must point at the **same host port** Docker publishes for Postgres. Default:

```text
POSTGRES_DB=aquapulse
POSTGRES_USER=aquapulse
POSTGRES_PASSWORD=aquapulse
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse
TEST_DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse_test
```

If something else already uses port `5432` (common on Windows), use `5433` in **three** places:

1. A root `.env` next to `docker-compose.yml`:

```text
POSTGRES_PORT=5433
POSTGRES_DB=aquapulse
POSTGRES_USER=aquapulse
POSTGRES_PASSWORD=aquapulse
```

2. `backend/.env`: set `POSTGRES_PORT=5433` and change both URLs to `127.0.0.1:5433`.

3. The `docker compose up` command in the next step (Compose reads the root `.env`).

Never commit a real `.env` file.

### 3. Start PostgreSQL (TimescaleDB + PostGIS)

```powershell
docker compose up -d
docker compose ps
```

Wait until `aquapulse-db` is `healthy`. Expected published port is `5432:5432`, or `5433:5432` if you overrode `POSTGRES_PORT`.

If Compose fails with `The container name "/aquapulse-db" is already in use`, an older container is still present. Start that one instead of creating a second:

```powershell
docker start aquapulse-db
docker ps --filter "name=aquapulse-db"
```

Do **not** run `docker compose down -v`. That deletes the `aquapulse_pgdata` volume.

### 4. Install backend dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You can skip `python -m venv` if `.venv` already exists.

### 5. Apply migrations

Still in `backend/` with the virtual environment active:

```powershell
alembic upgrade head
```

This must succeed before you start the API. Run it from `backend/` so Alembic finds `alembic.ini` and `backend/.env`.

### 6. Seed demonstration data (first run)

Still in `backend/` with the virtual environment active:

```powershell
python -m app.scripts.seed_database
```

Required on a new database. The command is idempotent: running it again updates the same demo organization, zones, assets, incidents, telemetry, and mock agent records. It does not create live detections or execute agents.

### 7. Start the backend (terminal 1)

From `backend/` with the virtual environment active:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this terminal open. Confirm:

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

PowerShell health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

macOS / Linux:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected:

```text
status: ok
database: connected
postgis: available
timescaledb: available
```

If `database` is not `connected`, the API is running but `DATABASE_URL` / `POSTGRES_PORT` do not match the container port.

### 8. Start the frontend (terminal 2)

From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Leave this terminal open. Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

`npm install` is only required the first time, or after `package.json` changes.

### 9. Confirm the tool is working

After both processes are running:

| Check | Expected |
| --- | --- |
| [http://127.0.0.1:5173](http://127.0.0.1:5173) | AquaPulse Overview dashboard loads |
| [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) | `ok`, database connected, PostGIS and TimescaleDB available |
| [http://127.0.0.1:8000/api/dashboard/summary](http://127.0.0.1:8000/api/dashboard/summary) | KPIs (after seed: 16 sensors, active incidents) |
| [http://127.0.0.1:8000/api/incidents](http://127.0.0.1:8000/api/incidents) | Seeded incidents (`INC-1833`–`INC-1842`) |
| [http://127.0.0.1:5173/incidents](http://127.0.0.1:5173/incidents) | Incident Center lists those incidents |
| [http://127.0.0.1:5173/map](http://127.0.0.1:5173/map) | Live Network Map |

Seeded telemetry ends at a frozen demo clock, so sensors can look stale or offline until you run the optional simulator. That is expected. The UI labels the data **Simulated telemetry**.

### Stop

- Backend / frontend: `Ctrl+C` in each terminal
- Database (keeps data): from the repository root, `docker compose stop`

Optional later commands (not required to open the app) are in the sections below: telemetry simulator, detection, tests, and database reset.

## 1. Prerequisites

- Python 3.11+
- Node.js 20+
- npm 10+
- Docker Desktop (or another Docker Engine with Compose v2)

## 2. Environment setup

From the repository root:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

`backend/.env` must include:

```text
DATABASE_URL=postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse
POSTGRES_DB=aquapulse
POSTGRES_USER=aquapulse
POSTGRES_PASSWORD=aquapulse
POSTGRES_PORT=5432
TELEMETRY_SIMULATOR_ENABLED=false
TELEMETRY_SIMULATOR_INTERVAL_SECONDS=5
TELEMETRY_SIMULATOR_SPEED=1
```

Never commit a real `.env` file.

## 3. Starting PostgreSQL

From the repository root:

```bash
docker compose up -d
```

Wait until `aquapulse-db` is healthy:

```bash
docker compose ps
```

If port 5432 is already used by a local PostgreSQL, set `POSTGRES_PORT=5433` in the root `.env` (for Docker Compose) and in `backend/.env` (for `DATABASE_URL` and tests), then start Compose again.

### Safe upgrade to TimescaleDB + PostGIS

The named volume `aquapulse_pgdata` is PostgreSQL 16 data and **must be kept**. Do **not** run `docker compose down -v`.

Confirmed image: `timescale/timescaledb-ha:pg16` (PostgreSQL 16, TimescaleDB, PostGIS). The HA image stores cluster files at `/home/postgres/pgdata/data`. Compose remounts the existing volume at that path.

1. Back up the current database (custom format):

```bash
docker exec aquapulse-db pg_dump -U aquapulse -Fc aquapulse > aquapulse-pre-timescale.dump
```

2. Recreate **only the container**, keeping the volume:

```bash
docker compose up -d --force-recreate aquapulse-db
```

3. Confirm the container is healthy and that existing counts are unchanged (35 assets, 9 incidents, geometries present).

4. If Postgres fails with a permission error, fix ownership of the volume **without deleting it**:

```bash
docker run --rm -v aquapulse_pgdata:/data alpine chown -R 1000:1000 /data
docker compose up -d aquapulse-db
```

5. Existing clusters created by `postgis/postgis` do not preload TimescaleDB. Compose now starts Postgres with `shared_preload_libraries=timescaledb`. For an already-initialized volume you can also append that setting to `postgresql.conf` and recreate the container **without** `-v`.

6. Apply the TimescaleDB migration and re-run the idempotent seed:

```bash
cd backend
alembic upgrade head
python -m app.scripts.seed_database
```

7. Confirm both extensions:

```bash
curl http://127.0.0.1:8000/api/health
# database: connected, postgis: available, timescaledb: available
```

Never treat volume deletion as the default fix. Only section 10 destroys `aquapulse_pgdata`, and only after an explicit `RESET` confirmation.

## 4. Installing backend dependencies

```bash
cd backend
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Running Alembic migrations

From `backend/` with the virtual environment active:

```bash
alembic upgrade head
```

This applies revisions through `0011_network_audit`. Revision ids are shortened because `alembic_version.version_num` is `varchar(32)`. The fourth revision enables TimescaleDB, creates the `sensor_readings` hypertable (1-day chunks), and does **not** drop the TimescaleDB extension on downgrade. `0010_maintenance_center` adds `maintenance_plans`, `maintenance_work_orders` and `maintenance_work_order_events`. Step 12 (`0011_network_audit`) adds append-only `agent_audit_events` and a nullable `agent_findings.anomaly_detection_id`. It does **not** create a network decision-engine table. Downgrade of `0011` removes only those Step 12 additions.

Roll back one revision:

```bash
alembic downgrade -1
```

Run Alembic from the `backend/` directory so it can load `alembic.ini` and application settings.

## 6. Seeding data

From `backend/` with the virtual environment active:

```bash
python -m app.scripts.seed_database
```

The command is idempotent. Running it twice updates the same organization, zones, assets, nine incidents (`INC-1833` through `INC-1842`), demonstration geometries, historical `sensor_readings`, six versioned detection rules, nine maintenance plans (`MPLAN-000001`–`MPLAN-000009`), six demonstration work orders (`MWO-000001`–`MWO-000006`), and nine device-network snapshots (`DNS-000001`–`000009`). It does not insert agent runs, findings, recommendations, or audit events. `SEED_AGENT_DEMO_DATA` defaults to false and never seeds dummy agent operational rows. It does not duplicate `incident_telemetry` (incident evidence) or sensor readings. It does not create detections or incidents from rules. It does not execute agents, live Nokia/CAMARA calls, notifications, or valve commands. It does not start the maintenance generator.

Historical sensor seed: 24 hours of 5-minute readings for all 16 sensors, ending at the frozen demo clock (`2026-09-01 07:45 UTC`). Offline sensors stop six hours before that clock. Values are deterministic and labelled `data_mode: simulated`.

You can also seed readings alone after a migration:

```bash
python -m app.scripts.seed_telemetry
```

## 6b. Development telemetry simulator

The simulator never starts with FastAPI and never runs during tests. It is disabled by default.

```text
TELEMETRY_SIMULATOR_ENABLED=false
TELEMETRY_SIMULATOR_INTERVAL_SECONDS=5
TELEMETRY_SIMULATOR_SPEED=1
```

One cycle:

```bash
python -m app.scripts.simulate_telemetry --once --enable
```

Limit to one sensor:

```bash
python -m app.scripts.simulate_telemetry --once --enable --sensor SNS-HBR-007
```

Continuous simulation (Ctrl+C to stop):

```bash
python -m app.scripts.simulate_telemetry --enable --interval 5
```

Optional `--count N` runs N cycles then exits. Production refuses to run unless `--enable` is passed. There is no public ingestion API; the CLI calls the internal telemetry service.

Scenarios must be selected explicitly (`--scenario`, default `normal`). Generated rows stay labelled `simulated`. The simulator never runs detection.

```bash
python -m app.scripts.simulate_telemetry --enable --sensor SNS-HBR-007 --scenario combined_leak_pattern --count 10
```

Scenarios: `normal`, `pressure_drop`, `flow_surge`, `combined_leak_pattern`, `connectivity_degradation`, `frozen_sensor`, `missing_telemetry`.

`missing_telemetry` skips inserts and does not delete existing readings. Anomaly scenarios with `--count` write spaced points (default `--spacing-minutes 3`) so a 30-minute rule window can see the pattern.

## 6c. Deterministic detection (Step 7)

The engine reads bounded TimescaleDB windows, evaluates versioned rules from `detection_rules`, stores reproducible evidence, and queues rows in `anomaly_detections`. Public IDs look like `DET-000001`.

It never starts with FastAPI and never runs during tests.

```bash
python -m app.scripts.run_detection --once --all
python -m app.scripts.run_detection --sensor SNS-HBR-007 --dry-run --explain
python -m app.scripts.run_detection --rule PRESSURE_DROP --window 60
```

`--dry-run` evaluates without writing. `--explain` prints concise evidence. The summary prints sensors checked, rules evaluated, detections created, detections deduplicated, and errors.

### Rules (demo thresholds)

| Code | Pattern | Demo threshold |
| --- | --- | --- |
| `PRESSURE_DROP` | Pressure falls in the window | 8% |
| `FLOW_SURGE` | Flow rises in the window | 12% |
| `COMBINED_LEAK_PATTERN` | Both in the same window | 8% drop and 12% surge |
| `CONNECTIVITY_DEGRADATION` | Packet loss, weak signal, or gaps | 10% loss, −100 dBm, or 15 min gap |
| `MISSING_TELEMETRY` | No new reading from a previously reporting sensor | 30 minutes |
| `SENSOR_QUALITY` | Out of range, frozen, or inconsistent | sensor metadata ranges / 15 min freeze |

`COMBINED_LEAK_PATTERN` uses reason code `combined_pressure_drop_and_flow_surge`. It is **not** a confirmed leak.

Scoring is a documented weighted sum (rule severity, magnitude beyond threshold, corroborating metrics, pipeline criticality, telemetry quality, asset health) clamped to 0–1. Priority bands: low < 0.35 ≤ medium < 0.55 ≤ high < 0.80 ≤ critical. Priority is not mapped to incident tiers.

### Deduplication / cooldown

Correlation key: `{sensor}:{rule}:{condition}`. While an active detection (`new` / `queued` / `under_review`) still has `condition_open=true`, repeats increment `repeat_count` instead of creating a new row. Default cooldown configuration is 60 minutes. After recovery (the rule stops firing), a later recurrence creates a new detection. Different rules may each create a row. Combined detections may list related single-metric detection numbers.

### Detection APIs

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/detections` | Filters: `status`, `priority`, `rule`, `sensor`, `zone`, `reason_code`, `start`, `end`, `search`, `sort_by`, `sort_order` |
| GET | `/api/detections/summary` | Queue counts and last-run stats |
| GET | `/api/detections/{detection_id}` | Public ID such as `DET-000001` |
| GET | `/api/detections/{detection_id}/evidence` | Structured evidence rows |
| GET | `/api/detections/{detection_id}/agent-input` | `InvestigationAgentInputV1` — does **not** invoke an agent |
| GET | `/api/map/detections` | Optional map layer (disabled in the UI by default) |

Unknown IDs return `{ "detail": { "message": "Detection not found", "code": "detection_not_found" } }`.

### Human investigation workflow (Step 8)

Detections remain separate from incidents. Operators investigate detections manually. Promotion is a human decision and does **not** confirm a leak. `actor_name` is a temporary development identity, not authentication.

Migrate:

```bash
alembic upgrade head
```

This applies `0006_detection_investigation` (append-only `detection_investigation_events` and workflow columns on `anomaly_detections`). Downgrade removes only those Step 8 additions.

| Current status | Allowed actions |
| --- | --- |
| `new` | start review, add note, dismiss, merge |
| `queued` | start review, add note, dismiss, merge |
| `under_review` | add note, dismiss, merge, promote |
| `dismissed` | add note, reopen (returns to `queued`) |
| `promoted` | view history only |
| `merged` | view history only |

Invalid transitions return HTTP `409` with `{ "detail": { "message": "...", "code": "..." } }`. Stable codes include `invalid_detection_transition`, `detection_already_promoted`, `detection_already_merged`, `invalid_merge_target`, `detection_merge_self`, `incident_promotion_conflict`. Validation errors are `422`. Missing detections or merge targets are `404`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/detections/{id}/review` | Start investigation |
| POST | `/api/detections/{id}/notes` | Add a note (does not change status) |
| POST | `/api/detections/{id}/dismiss` | Dismiss with a required reason |
| POST | `/api/detections/{id}/reopen` | Reopen a dismissed detection to `queued` |
| POST | `/api/detections/{id}/merge` | Merge into another active detection |
| POST | `/api/detections/{id}/promote` | Create and link an incident |
| GET | `/api/detections/{id}/history` | Chronological investigation events (`DIE-000001`) |

Every mutation body requires `actor_name` (non-empty trimmed string, max 120). This is **not** a user, session, password, token or role.

Example promote:

```json
{
  "actor_name": "Demo Supervisor",
  "title": "Suspected leak near Harbour District",
  "severity": "tier_2",
  "classification": "suspected_leak",
  "summary": "Promoted after manual review of corroborating pressure and flow evidence.",
  "note": "Operator confirmed that further field investigation is required."
}
```

Promotion runs in one database transaction: lock the detection, require `under_review`, create the next `INC-` number using the existing incident model, copy context (not Timescale raw readings), set status `promoted`, link `incident_id`, append a `promoted` investigation event and an incident timeline event, then commit. If any step fails, the transaction rolls back. Repeating promote returns `409` with the already-linked incident ID and does not create another incident.

Merge does not rewrite evidence. The source becomes `merged` and points at the target; the target stays active.

The Investigation Queue (`/detections`) exposes one contextual action per row. Detection details (`/detections/:id`) contain the investigation panel, confirmation dialogs, and immutable history.

Seed is idempotent. If `DET-000002` exists and is still `new`, seed starts a demonstration review. It never pre-promotes a detection and does not change the nine seeded incidents unless an operator calls promote.

Remaining limitations: no authentication/RBAC, no notifications, no AI agents, no CAMARA, no valve commands, no automatic incident creation.

`GET /api/detections/{id}/agent-input` returns the versioned future Investigation Agent contract (schema version `1`) built from the stored detection. `agent_executed` is always `false`.

Frontend:

- `/detections` — Investigation Queue (sidebar, near Incidents)
- `/detections/:detectionId` — Detection Details

The dashboard shows new detections awaiting investigation. The Live Map has a **Detections** layer (off by default, square `D` markers, distinct from incident `!` markers). Incident Center links to the queue and does not merge the tables. Seeded incidents are not fabricated into detections.

### Operations Center (Step 9)

Operations are **human-recorded workflow events**. AquaPulse does not execute valve, isolation or pressure commands. `actor_name` is a temporary development identity, not authentication. Agents, CAMARA, notifications and authentication remain postponed.

A detection is not a confirmed incident. Promotion remains a human decision. Recording `leak_repaired` in a resolution summary is an operator statement, not proof that AquaPulse repaired infrastructure.

Migrate:

```bash
alembic upgrade head
```

This applies `0007_incident_operations` (operational columns on `incidents`, `incident_response_tasks`, and `actor_name` / `response_task_id` on the existing append-only incident timeline). Downgrade removes only those Step 9 additions. Legacy `monitoring` statuses are preserved. Assignment continues to use the existing `assigned_operator` field.

| Current status | Allowed actions |
| --- | --- |
| `open` | acknowledge, assign, add note |
| `acknowledged` | assign, start investigation, add note |
| `investigating` | assign, add note, request approval, start response, resolve, false alarm |
| `awaiting_approval` | assign, add note, start response, return to investigation |
| `responding` | assign, add note, manage tasks, resolve |
| `monitoring` | assign, add note, start response, resolve, false alarm (legacy, not migrated) |
| `resolved` | view history, reopen |
| `false_alarm` | view history, reopen |

Response tasks: `todo` → `start` → `in_progress` → `complete` or `cancel`. Completed or cancelled tasks cannot return to `todo`. Tasks can be created only while the incident is `responding`. Resolve with open tasks returns `409` `incident_incomplete_tasks` unless `confirm_incomplete_tasks` is true.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/incidents/{id}/acknowledge` | Acknowledge (`open` → `acknowledged`; already acknowledged is idempotent) |
| POST | `/api/incidents/{id}/assign` | Assign or reassign |
| POST | `/api/incidents/{id}/start-investigation` | Begin investigation, or return from awaiting approval |
| POST | `/api/incidents/{id}/request-approval` | Move to `awaiting_approval` |
| POST | `/api/incidents/{id}/start-response` | Begin coordinated response (assignment required) |
| POST | `/api/incidents/{id}/notes` | Add an operational note without changing status |
| POST | `/api/incidents/{id}/resolve` | Resolve with a required summary |
| POST | `/api/incidents/{id}/false-alarm` | Mark false alarm (evidence is kept) |
| POST | `/api/incidents/{id}/reopen` | Reopen a terminal incident to `open` |
| GET | `/api/incidents/{id}/operations` | Operational state and allowed actions |
| GET/POST | `/api/incidents/{id}/tasks` | List or create response tasks |
| PATCH | `/api/incidents/{id}/tasks/{task_id}` | Edit safe task fields |
| POST | `/api/incidents/{id}/tasks/{task_id}/start` | Start a task |
| POST | `/api/incidents/{id}/tasks/{task_id}/complete` | Complete a task |
| POST | `/api/incidents/{id}/tasks/{task_id}/cancel` | Cancel a task |
| GET | `/api/operations/queue` | Operations Center work queue |

Every mutation requires `actor_name` (trimmed, max 120). This is **not** authentication.

Example acknowledgement:

```json
{
  "actor_name": "Demo Operator",
  "note": "Control room acknowledged the incident."
}
```

Example resolution:

```json
{
  "actor_name": "Demo Supervisor",
  "resolution_code": "leak_repaired",
  "resolution_summary": "Damaged connection replaced and pressure returned to normal.",
  "confirm_incomplete_tasks": true
}
```

Each mutation locks the incident (and task) row, validates the transition, updates state, appends a timeline event, and commits together. Failure rolls back the whole transaction. Invalid transitions return HTTP `409`. Missing incidents or tasks return `404`. Validation errors return `422`.

Pages to review:

- `/operations` — Operations Center
- `/incidents/:incidentId` — Incident Details operations panel
- `/` — Overview KPIs now include awaiting-approval, responding and overdue-task counts from PostgreSQL

Seed remains idempotent. Existing public IDs are unchanged. Demonstration state uses the nine seeded incidents: one unacknowledged (`INC-1838`), one acknowledged (`INC-1836`), investigating and awaiting-approval rows, one responding incident with mixed tasks including an overdue task, plus the existing resolved and false-alarm records.

### Analytics (Step 10)

Telemetry is **simulated**. Estimated monitored volume is **not** confirmed consumption, NRW or water loss. Analytics is read-only and does **not** make operational decisions. Authentication, notifications, agents and CAMARA remain postponed.

Analytics windows are anchored to the frozen demonstration clock `2026-09-01 07:45 UTC`. Supported ranges are `24h`, `7d` and `30d`. Each range is compared with the immediately preceding period of equal length. Default buckets: 24h → 30 minutes, 7d → 6 hours, 30d → 1 day.

**Estimated monitored volume** integrates each simulated flow sample over the 5-minute seed interval: `Σ(flow_lps × 300) / 1000`. Missing samples are not interpolated.

The historical seed now covers **30 days** at 5-minute intervals. The most recent 24 hours keep the original deterministic pattern, sensor IDs, offline-sensor gap and `source_message_id` values. All generated readings are marked `data_mode: simulated`.

No new Alembic revision is required. Re-seed after pulling Step 10:

```bash
python -m app.scripts.seed_database
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/analytics/overview` | KPI cards and previous-period comparison |
| GET | `/api/analytics/telemetry` | Pressure, flow, quality and completeness |
| GET | `/api/analytics/zones` | Zone comparison table |
| GET | `/api/analytics/detections` | Detection trends and distributions |
| GET | `/api/analytics/incidents` | Incident trends and classifications |
| GET | `/api/analytics/operations` | Acknowledgement, response and resolution times |
| GET | `/api/analytics/assets` | Asset-health and connectivity distribution |

Common query parameters: `range=24h\|7d\|30d`, optional `zone`, optional `sensor`, optional validated `interval`. Invalid range or interval returns `422`. Unknown zone or sensor returns `404`.

Durations are `null` when the required timestamps do not exist. Empty previous telemetry windows are `null`, not `0`. Higher packet loss is not labelled as an improvement.

Zone CSV export is generated in the browser from the current table, including `generated_at` and `data_mode`.

Pages to review:

- `/analytics` — Analytics
- `/` — Overview now links to Analytics and shows a 24-hour pressure comparison
- `/map?zone=...` — zone drill-down from the comparison table

### Agent Integration Readiness (Step 11)

AquaPulse exposes versioned Investigation and Response Agent contracts so those services can be connected later. **Agent execution is disabled.** Investigation results are advisory evidence. Response results are recommendations. Agent severity does not authorize actuation. CAMARA network permission does not authorize valve control. Human approval must occur before any future physical execution. AquaPulse remains the authority for incidents and infrastructure actions. All external actions are disabled in Step 11.

Architecture boundary: friends expose HTTP, provide a base URL, set environment variables, run contract tests, and enable a feature flag later. They do not need AquaPulse’s database or frontend. An adapter layer maps internal models to external contracts. SQLAlchemy models are not leaked into agent payloads.

Modes: `disabled` (default), `mock`, `remote`. Remote URLs come only from trusted configuration, never from a request parameter. Timeouts are explicit. Advisory HTTP may retry a bounded number of times. Physical-command requests are never retried automatically. Idempotency keys are `idempotency_key`, `batch_id`, `anomaly_id`, and `result_id`.

Identity mappings live in `integration_identity_mappings`. Unknown external IDs are stored as `unmapped` with a structured warning. AquaPulse never guesses a mapping.

Alembic revision: `0008_agent_integration_readiness`. Re-seed after upgrading:

```bash
cd backend
alembic upgrade head
python -m app.scripts.seed_database
```

Feature flags default to off. See `backend/.env.example`. AquaPulse does not require `GROQ_API_KEY`.

Contract-check and offline validation:

```bash
python -m app.scripts.check_agent_contract --agent investigation --base-url http://127.0.0.1:9001
python -m app.scripts.check_agent_contract --agent response --base-url http://127.0.0.1:9002
python -m app.scripts.validate_agent_fixture --agent investigation --file contracts/agents/investigation/v1/valid-response.json
```

Friend HTTP interface: Investigation `GET /health`, `GET /v1/contract`, `POST /v1/investigate`. Response `GET /health`, `GET /v1/contract`, `POST /v1/recommend-response`. Copy `backend/examples/investigation_agent_wrapper.py` or `backend/examples/response_agent_wrapper.py`. Guide: `AGENT_INTEGRATION_GUIDE.md`.

Future activation: set the trusted URL, switch mode to `remote`, enable the agent flag, and run contract checks. Do not enable physical commands, CAMARA, or real notifications from this step.

Pages to review:

- `/integrations` — Integration Readiness (read-only)
- `/agents` remains the postponed AI Agents placeholder

### Device location and cellular identity (Step 11.1)

Every device (sensor, valve, gateway) has a **direct** `zone_id` on `assets`, already present from the initial schema and verified by migration `0009_device_location` (file `0009_device_location_connectivity.py`). Public zone IDs use `ZONE-{code}` (for example `ZONE-HBR` for Dubai Harbour). Internal database UUIDs are not exposed. Existing zone public codes (`HBR`, `CRN`, …) are unchanged.

New nullable columns on `assets`:

- `location_label` — human-readable site description, maximum 160 characters
- `device_msisdn` — device SIM identity in E.164 (`+[country code][subscriber number]`), maximum 16 characters including `+`. Empty strings store as `null`. Non-null values are unique.

`device_msisdn` is **not** an operator phone number and is **not** `operator_contact`. A device SIM and an on-call operator contact are different concepts. Public asset and map APIs return only `device_msisdn_masked` (for example `+971•••••4821`). The raw value is never returned there. Numbers in the seed are **fictional demonstration values** only. Seed does not overwrite a non-demo MSISDN on later runs.

If a pipeline segment is present, it must belong to the same zone as the asset. The migration and seed fail with a diagnostic instead of guessing a zone.

Asset list, detail and map responses add `zone_id`, `zone_name`, `location_label`, `has_cellular_identity` and `device_msisdn_masked`. The existing `zone` filter still matches the zone name and now uses the direct `assets.zone_id` relationship.

Agent contract `1.0` is unchanged. Device location and MSISDN are not added to external agent schemas in this step. A future authorized contract may receive them only when explicitly required.

### Maintenance Center (0010)

Maintenance records describe **human work**. Completing a work order does **not** execute a physical device command and does **not** automatically change asset operational status, valve position, sensor health or incident status. `actor_name` is a temporary development identity, not authentication. Authentication, notifications, CAMARA, live agents and automatic background scheduling remain postponed. This increment is present and was not expanded in Step 12.

Migrate:

```bash
alembic upgrade head
```

This applies `0010_maintenance_center` after `0009_device_location`. Downgrade removes only the three Maintenance Center tables.

#### Tables

`maintenance_plans`

- Public IDs `MPLAN-000001`
- One asset may have several plans for different maintenance types
- `interval_days` must be positive
- Disabled plans do not generate work orders
- Plans are never physically deleted through the API

`maintenance_work_orders`

- Public IDs `MWO-000001`
- Optional `maintenance_plan_id` and `incident_id`
- Statuses: `scheduled`, `assigned`, `in_progress`, `completed`, `cancelled`
- Overdue is derived, never stored: `due_at < reference_time AND status NOT IN (completed, cancelled)`
- Completed orders require `completed_at`, `completed_by`, `completion_result` and a non-empty summary
- Cancelled orders require `cancelled_at`, `cancelled_by` and a reason
- No hard-delete endpoint

`maintenance_work_order_events`

- Public IDs `MWE-000001`
- Append-only history
- Plan events may set `plan_id` with a nullable `work_order_id`

#### Plan lifecycle

Plans define recurring schedules. They do **not** run automatically and FastAPI does not start the generator.

| Action | Result |
| --- | --- |
| Create | Enabled plan with `next_due_at` and a `plan_created` event |
| Update | Safe field changes and a `plan_updated` event |
| Disable | `enabled=false`, `plan_disabled` event, no further generated work |

Manual generator (idempotent; at most one open work order per due plan cycle):

```bash
python -m app.scripts.generate_maintenance_work_orders --as-of 2026-09-01T07:45:00Z
```

It prints `created`, `skipped` and `errors`. It never starts or completes work. It advances `next_due_at` by `interval_days` after creating an order.

#### Work-order lifecycle

| Current status | Allowed actions |
| --- | --- |
| `scheduled` | assign, reschedule, add note, start, cancel |
| `assigned` | reassign, reschedule, add note, start, cancel |
| `in_progress` | add note, complete, cancel |
| `completed` | view only |
| `cancelled` | view only |

Starting work sets `started_at`. Starting an unassigned order requires `assigned_to` or `confirm_unassigned=true`. Completing with `completed_successfully`, `asset_repaired`, `asset_replaced`, `no_fault_found` or `other` updates `assets.last_maintenance_at` and recalculates `assets.next_maintenance_at` from the next enabled plan. `follow_up_required` and `unable_to_complete` leave the asset unchanged. Completing maintenance never resolves an incident.

Invalid transitions return HTTP `409`. Missing records return `404`. Invalid payloads return `422`. State update and history event commit together under row locking.

Summary APIs return `reference_time`. Demonstration summaries use the frozen demo clock `2026-09-01 07:45 UTC`. Newly performed runtime actions stamp the live UTC clock.

#### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/maintenance/summary` | KPI counts and `reference_time` |
| GET | `/api/maintenance/work-orders` | Filtered queue |
| GET | `/api/maintenance/work-orders/upcoming` | Grouped upcoming list |
| GET | `/api/maintenance/work-orders/{id}` | Detail and history |
| GET | `/api/maintenance/work-orders/{id}/history` | Append-only events |
| POST | `/api/maintenance/work-orders` | Create |
| POST | `/api/maintenance/work-orders/{id}/assign` | Assign or reassign |
| POST | `/api/maintenance/work-orders/{id}/reschedule` | Change due date |
| POST | `/api/maintenance/work-orders/{id}/start` | Start work |
| POST | `/api/maintenance/work-orders/{id}/notes` | Note without status change |
| POST | `/api/maintenance/work-orders/{id}/complete` | Complete (administrative) |
| POST | `/api/maintenance/work-orders/{id}/cancel` | Cancel with reason |
| GET | `/api/maintenance/plans` | List plans |
| GET | `/api/maintenance/plans/{id}` | Plan detail |
| POST | `/api/maintenance/plans` | Create plan |
| PATCH | `/api/maintenance/plans/{id}` | Update plan |
| POST | `/api/maintenance/plans/{id}/disable` | Disable plan |
| GET | `/api/assets/{asset_id}/maintenance` | Active plans, open and recent work |
| GET | `/api/incidents/{incident_id}/maintenance` | Related work orders |

Filters: `status`, `priority`, `maintenance_type`, `asset_type`, `asset_id`, `zone`, `assigned_to`, `overdue`, `due_from`, `due_to`, `search`, `sort_by`, `sort_order`.

Every mutation requires `actor_name` (trimmed, max 120). This is **not** authentication.

Example completion:

```json
{
  "actor_name": "Demo Operator",
  "completion_result": "completed_successfully",
  "completion_summary": "Inspected flange and recorded no leak.",
  "confirm": true
}
```

Stable error codes: `maintenance_work_order_not_found`, `maintenance_plan_not_found`, `invalid_maintenance_transition`, `maintenance_assignment_required`, `maintenance_completion_required`, `maintenance_cancellation_reason_required`, `maintenance_duplicate_open_order`, `maintenance_plan_disabled`, `maintenance_concurrent_update`, `asset_not_found`.

#### Seed examples

- `MWO-000001` — overdue critical corrective on `VLV-CRN-014`, linked to `INC-1842`
- `MWO-000002` — due within 7 days on `SNS-HBR-007`
- `MWO-000003` — assigned
- `MWO-000004` — in progress
- `MWO-000005` — completed successfully
- `MWO-000006` — cancelled
- `MPLAN-000006` — enabled and due (used by the manual generator)
- `SNS-RUH-078` — asset without a plan

Existing asset IDs, incident IDs, detection data, device zones, PostGIS geometry, MSISDN values and agent contracts are unchanged.

Pages to review:

- `/maintenance` — Maintenance Center
- `/maintenance/work-orders/:workOrderId` — Work Order Details
- `/assets/:assetId` — Asset Details maintenance section
- `/incidents/:incidentId` — related maintenance (read-only)

### Device Network Health (Nokia / CAMARA)

**Network Health does not use an agent.** The `/network-health` page monitors AquaPulse devices using snapshots stored in PostgreSQL. Future live data comes from **Nokia Network as Code / CAMARA APIs called only by the AquaPulse backend**. React never calls Nokia or RapidAPI. Investigation Agent, Response Agent and Network Agent are not involved.

The current environment uses **demonstration / simulator data**. `NOKIA_NETWORK_API_ENABLED` defaults to `false` and `NOKIA_NETWORK_API_MODE` defaults to `mock`. The API starts without Nokia credentials.

| Information | Source |
| --- | --- |
| Device identity/type | `assets` |
| Zone and registered location | PostgreSQL / PostGIS |
| Phone / MSISDN | `assets.device_msisdn` (masked in public APIs) |
| Reachability | Nokia Device Reachability API via backend provider |
| Network-derived location | Nokia Location Retrieval API via backend provider |
| Last sensor reading | TimescaleDB |
| Incident status | AquaPulse incident workflow |

Important distinctions:

- Nokia reachability (`reachable` / `unreachable` / `unknown`) is **not** incident status (`investigating` / `awaiting_approval` / `resolved`).
- The registered PostGIS point remains the authoritative installation location for fixed infrastructure.
- A Nokia location is a network-derived observation with an accuracy radius. It does **not** replace the registered location and is not GPS-level precision.
- Devices without an MSISDN cannot use these Nokia APIs (`not_supported`).
- Refresh never triggers agents, incidents, notifications or valve commands.

#### Provider architecture

Routes depend on `DeviceNetworkProvider`:

- `DisabledDeviceNetworkProvider`
- `MockNokiaDeviceNetworkProvider` (default)
- `HttpNokiaDeviceNetworkProvider` (live HTTP, credentials required)

Nokia/RapidAPI details stay in the HTTP adapter, not in FastAPI routes.

#### Environment

```text
NOKIA_NETWORK_API_ENABLED=false
NOKIA_NETWORK_API_MODE=mock
NOKIA_NETWORK_API_BASE_URL=
NOKIA_NETWORK_API_KEY=
NOKIA_NETWORK_API_HOST=
NOKIA_LOCATION_PATH=/location-retrieval/v0.3/retrieve
NOKIA_REACHABILITY_PATH=/device-reachability-status/v0.7/retrieve
NOKIA_NETWORK_TIMEOUT_SECONDS=10
NOKIA_NETWORK_CACHE_SECONDS=300
```

Modes:

- `mock` (default, including when the API is disabled) → `source_mode: seeded_demo`
- `simulator` → `source_mode: nokia_simulator`
- `live` with a trusted base URL and key → `source_mode: nokia_live`
- `disabled` → no external lookup (`not_checked`)

Remote URLs come only from this trusted configuration. Requests use explicit timeouts and a bounded retry for safe retrieval only. Tests must not call the internet.

**Privacy:** public APIs never return a raw MSISDN or unsanitized Nokia payloads. API keys and authorization headers are redacted recursively before storage. Human-readable logs store only masked identifiers. Location data is sensitive.

**Authentication / authorization for these endpoints is a documented future production requirement.** It is not implemented here.

**Exposed-key warning:** if a Nokia / RapidAPI key was visible in a screenshot, chat, repository or ticket, revoke it and generate a replacement. Do not commit keys. Do not paste a live key into `.env.example`.

#### Location Retrieval

The backend identifies the device with its normalized E.164 MSISDN (`device.phoneNumber`). The normalized result includes latitude, longitude, accuracy radius, area type, observation time and retrieval time. Do not treat this as a GPS fix.

#### Device Reachability

The backend normalizes Nokia `reachable` plus optional `connectivity` (`data` / `sms`) and a checked timestamp. A subscription-management response is **not** current reachability state.

#### Cache and refresh

`GET /api/network-health/summary` and `GET /api/network-health/devices` read stored latest snapshots. `POST /api/network-health/devices/{asset_id}/refresh` and bounded `POST /api/network-health/refresh` call the injected provider unless a snapshot is still inside `NOKIA_NETWORK_CACHE_SECONDS` (override with `force=true`). Bulk refresh is concurrency-limited and may return partial success.

#### Persistence

`0013_device_network` adds `device_network_snapshots` (`DNS-000001`). It does not modify `agent_audit_events` or historical `NETEVT-*` records. Historical Network Agent logs remain available at the compatibility event endpoints; they are not shown as current device health.

#### APIs

- `GET /api/network-health/summary` — latest device-network counts
- `GET /api/network-health/devices` — latest snapshot per device
- `GET /api/network-health/devices/{asset_id}` — device network details
- `GET /api/network-health/devices/{asset_id}/history` — snapshot history
- `POST /api/network-health/devices/{asset_id}/refresh` — safe backend refresh
- `POST /api/network-health/refresh` — bounded bulk refresh
- `GET /api/incidents/{incident_id}/device-network` — stored context for the affected device
- `POST /api/incidents/{incident_id}/device-network/refresh` — refresh that device only
- `GET /api/network-health/events` — historical Network Agent audit compatibility
- `GET /api/network-health/events/{event_id}` — historical event detail

Incident list location continues to use the mapped asset / segment / zone stored in AquaPulse. Nokia refresh does not rewrite incident locations.

### Agent-Native Unified Audit Trail (Step 12)

AquaPulse stores, maps, displays and enforces safety around agent outputs. It does **not** confirm anomalies, classify instrument faults, calculate final confidence or severity, decide QoD/CAMARA actions, choose a Response Agent decision, or decide valve isolation. The Network Health page is no longer an agent log view.

Existing deterministic detection is the lightweight screening model. Its priority is labelled **Screening priority**. Investigation Agent classification, severity, confidence and justification are shown separately when a finding is mapped. Findings never automatically promote a detection, create an incident, change detection status, or trigger the Response Agent.

#### Persistence

`0011_network_audit` reuses `agent_integrations`, `agent_runs`, `agent_findings`, `agent_response_recommendations` and `integration_identity_mappings`. It adds append-only `agent_audit_events` (`AAE-000001`) and a nullable `agent_findings.anomaly_detection_id`. There is no `network_observations` table and no AquaPulse network decision engine.

Network Management Agent outputs use a draft envelope (`schema_version: draft-unconfirmed`). Allowed presentation labels: `connectivity_check`, `qod_requested`, `qod_granted`, `qod_denied`, `qod_released`, `agent_error`. These are provisional logs, not a finalized contract.

#### Mock pipeline (database-backed)

Seeded, idempotent, and never executed against live agents:

- Example A (`AGRUN-000204`): Tier 1 `confirmed_instrument_fault`, unreachable, `ESCALATE_UNREACHABLE`, no valve action
- Example B (`AGRUN-000205`): Tier 1 instrument fault with stale data, `ALERT_AND_AWAIT`, advisory only
- Example C (`AGRUN-000203`): Tier 3 `confirmed_anomaly`, mock QoD grant, `AUTONOMOUS_ISOLATE` blocked by AquaPulse safety. Valve state unchanged. Notification not sent.

NEOM cluster IDs (`cluster-desert-042`–`044`) remain unmapped. They are not attached to Harbour, Al Ain or Corniche devices.

The Response Agent graph is stored exactly as reported: `reachability_check → llm_response_planner → execute_response → human_override → audit_writer`. AquaPulse then records a separate platform safety result. Mock valve or notification results are labelled unverified.

#### Read-only APIs

- `GET /api/agent-audit/summary`
- `GET /api/agent-audit/runs`
- `GET /api/agent-audit/runs/{run_id}`
- `GET /api/agent-audit/events`
- `GET /api/agent-audit/events/{event_id}`

List endpoints omit large raw payloads. Detail endpoints return sanitized structured payloads. Secrets, tokens, raw MSISDNs, operator contacts, local paths and internal URLs are redacted. `reasoning_trace` is only agent-provided text, labelled unverified.

Agent feature flags remain disabled. Device Network Health refresh endpoints do not execute agents.

## 7. Starting FastAPI

Use the full sequence in [How to run AquaPulse locally](#how-to-run-aquapulse-locally) the first time. Then, from `backend/` with the virtual environment active:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs

## 8. Starting React

The API on port `8000` must already be running. From `frontend/`:

```bash
npm install
npm run dev
```

- App: http://127.0.0.1:5173

The frontend reads `VITE_API_URL` and defaults to `http://localhost:8000`.

## 9. Stopping the database

From the repository root:

```bash
docker compose stop
```

This keeps the `aquapulse_pgdata` volume so incident data remains.

## 10. Resetting the development database

This destroys **only** the local Docker volume `aquapulse_pgdata` used by the `aquapulse-db` service. It does not touch a production database.

PowerShell:

```powershell
$confirm = Read-Host "Type RESET to destroy the local AquaPulse development database volume aquapulse_pgdata"
if ($confirm -eq "RESET") { docker compose down -v }
```

macOS / Linux:

```bash
read -r -p "Type RESET to destroy the local AquaPulse development database volume aquapulse_pgdata: " confirm
if [ "$confirm" = "RESET" ]; then docker compose down -v; fi
```

After a reset, start PostgreSQL again, then rerun `alembic upgrade head` and `python -m app.scripts.seed_database`.

## 11. Running backend tests

Tests use a separate database (`aquapulse_test` by default) and never modify `aquapulse`.

From `backend/` with the virtual environment active and PostgreSQL running:

```bash
pytest
```

Optional override:

```bash
$env:TEST_DATABASE_URL = "postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:5432/aquapulse_test"
pytest
```

## 12. Running the frontend build

From `frontend/`:

```bash
npm run build
```

## Available API endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Application health, including `database`, `postgis`, and `timescaledb` |
| GET | `/api/health/database` | Database-only health (`503` when PostgreSQL is unreachable) |
| GET | `/api/dashboard/summary` | Overview KPIs (incident counts, sensor totals, network health from telemetry) |
| GET | `/api/dashboard/telemetry` | TimescaleDB network series (`range=1h\|6h\|24h`, `data_mode: simulated`) |
| GET | `/api/incidents` | Filtered, sorted incident list |
| GET | `/api/incidents/{incident_id}` | Incident details (`INC-1835` style public IDs) |
| GET | `/api/incidents/{incident_id}/timeline` | Incident timeline |
| GET | `/api/assets` | Read-only asset registry (includes public `zone_id`, location label, masked cellular identity) |
| GET | `/api/assets/{asset_id}` | Asset details (`SNS-HBR-007` style public IDs), including `device_location` |
| GET | `/api/assets/{asset_id}/incidents` | Incidents related to an asset |
| GET | `/api/assets/{asset_id}/health` | Sensor TimescaleDB series, or `mock_recent_health` for valves/gateways |
| GET | `/api/telemetry/sensors/{sensor_id}` | Sensor history (`start`, `end`, `range`, `interval`, `metrics`, `limit`) |
| GET | `/api/telemetry/sensors/{sensor_id}/latest` | Latest reading and freshness |
| GET | `/api/telemetry/sensors/latest` | Batched latest readings for all sensors |
| GET | `/api/telemetry/network/summary` | Network telemetry summary |
| GET | `/api/map/zones` | GeoJSON zone boundaries |
| GET | `/api/map/pipelines` | GeoJSON pipeline segments |
| GET | `/api/map/assets` | GeoJSON assets (sensors include latest telemetry freshness) |
| GET | `/api/map/incidents` | GeoJSON incidents (resolved/false-alarm excluded by default) |
| GET | `/api/map/summary` | Visible feature counts (`data_mode: seeded_demo`) |
| GET | `/api/map/nearby` | PostGIS distance search around a point |
| GET | `/api/integrations/agents/readiness` | Agent integration readiness (no secrets or URLs) |
| GET | `/api/integrations/agents` | Configured agent integrations |
| GET | `/api/integrations/agents/runs` | Read-only agent run history |
| GET | `/api/integrations/agents/findings` | Advisory investigation findings |
| GET | `/api/integrations/agents/recommendations` | Response recommendations |
| GET | `/api/integrations/compat/v1/device-reachability/{device_id}` | Mock reachability for mapped devices |
| POST | `/api/integrations/compat/v1/qod/{device_id}/reserve` | Mock/denied CAMARA QoD |
| POST | `/api/integrations/compat/v1/notify` | Validate-only notify (`sent: false`) |
| POST | `/api/integrations/compat/v1/valve/isolate` | Always blocked in Step 11 |
| GET | `/api/integrations/compat/v1/valve/status/{device_id}` | Read-only mapped valve position |

Map query parameters include `zone`, `asset_type`, `asset_status`, `incident_severity`, `incident_status`, and `include_resolved`. Nearby requires `latitude`, `longitude`, and `radius_m` (maximum 25 km).

Telemetry history query parameters:

- `range` — `1h`, `6h`, `24h`, `7d`
- `interval` — `raw`, `1m`, `5m`, `15m`, `1h` (`time_bucket` for aggregates)
- `metrics` — comma-separated: `pressure`, `flow`, `temperature`, `signal`, `packet_loss`, `battery`
- `start` / `end` — explicit UTC window (maximum 7 days)
- `limit` — capped at 2000 points

### Freshness rules

Measured against wall-clock UTC at query time, defined in `backend/app/services/telemetry_constants.py`:

- **fresh** — last reading within 15 minutes
- **stale** — last reading within 2 hours
- **offline** — no reading, or last reading older than 2 hours

The historical seed ends at the frozen demo clock, so sensors look stale/offline until the development simulator inserts newer rows. This is expected. The UI labels the data **Simulated telemetry**.

### Compression and retention plan (not activated)

- Hypertable chunk interval: **1 day**
- Intended compression: after **7 days** (not enabled in this step)
- Intended raw retention: **90 days**
- Aggregates would be kept longer

Automatic deletion is **not** enabled. Do not add a retention job that drops seeded data.

Frontend routes:

- `/map` — Live Network Map
- `/pipeline-lab` — Water-pipeline testbed digital twin (embedded dashboard)
- `/assets` — Asset Registry
- `/assets/:assetId` — Asset Details
- `/maintenance` — Maintenance Center
- `/maintenance/work-orders/:workOrderId` — Work Order Details
- `/incidents` — Incident Center
- `/incidents/:incidentId` — Incident Details
- `/detections` — Investigation Queue
- `/detections/:detectionId` — Detection Details
- `/integrations` — Integration Readiness
- `/network` and `/network-health` — Device network health (demonstration / simulator data)
- `/agent-audit` — Unified Agent Audit Trail
- `/agent-audit/runs/:runId` — Agent audit run details
- `/agents` — AI Agents placeholder (not the integration gateway)

Frontend map environment variables (`frontend/.env`):

```text
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_MAP_ATTRIBUTION=© OpenStreetMap contributors
```

Development tiles are OpenStreetMap. Attribution is shown on the map. Do not commit a private tile token.

Asset list query parameters:

- `asset_type` — `sensor`, `valve`, or `gateway`
- `status` — `online`, `degraded`, or `offline`
- `zone` — zone name, for example `Dubai Harbour`
- `search` — matches external ID, name, manufacturer, model, serial number, location label, or zone
- `maintenance` — `due`, `upcoming`, or `scheduled`
- `sort_by` — `name`, `asset_type`, `status`, `health_score`, `last_seen`, or `next_maintenance`
- `sort_order` — `asc` or `desc`

Unknown asset IDs return HTTP 404 with `{ "detail": { "message": "Asset not found", "code": "asset_not_found" } }`.

The asset inventory is read-only until authentication and operational workflows exist. There are no POST, PATCH, or DELETE asset endpoints.

## Project structure

```text
aquapulse/
├── frontend/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── detection/
│   │   ├── repositories/
│   │   ├── scripts/
│   │   └── services/
│   └── tests/
├── docker-compose.yml
├── README.md
└── .gitignore
```

## Troubleshooting

### Docker Desktop is not running

On Windows, `docker compose` can hang or return no output if Docker Desktop is stopped. Start Docker Desktop, wait until `docker info` prints a server version, then retry `docker compose up -d`.

### Container name `/aquapulse-db` already in use

Compose creates a container named `aquapulse-db`. If that name already exists from an earlier checkout:

```powershell
docker start aquapulse-db
docker ps --filter "name=aquapulse-db"
```

Confirm the published host port (`5432` or `5433`) matches `DATABASE_URL` in `backend/.env`. Do not delete the volume to fix this.

### API starts but health shows database not connected

`POSTGRES_PORT` in `backend/.env` and `DATABASE_URL` must match the port published by `aquapulse-db`. Example: if `docker ps` shows `0.0.0.0:5433->5432/tcp`, the URL host port is `5433`.

### TimescaleDB + PostGIS image and existing volume

The development volume `aquapulse_pgdata` is PostgreSQL 16 data. Recreating the container with `timescale/timescaledb-ha:pg16` reuses that volume at `/home/postgres/pgdata/data`. After `docker compose up -d --force-recreate aquapulse-db`, confirm:

```bash
docker compose ps
# IMAGE should be timescale/timescaledb-ha:pg16 and STATUS healthy
```

Then run `alembic upgrade head`. Migration `0004_timescaledb_sensor_readings` creates the TimescaleDB extension and hypertable. It does not recreate the cluster and does not drop PostGIS.

Do **not** delete `aquapulse_pgdata` as the default upgrade step.

If Postgres refuses to start because files are owned by UID 999 (the previous PostGIS image) while the HA image uses UID 1000, change ownership of the volume without deleting it (see section 3).

If `CREATE EXTENSION timescaledb` fails, the running image is still `postgis/postgis` without Timescale. Recreate **only the container**:

```bash
docker compose up -d --force-recreate aquapulse-db
```

If `CREATE EXTENSION postgis` fails after the image change, confirm the HA tag includes PostGIS (`pg16`, not a Timescale-only OSS image without PostGIS). Do not wipe the volume.

If the volume was initialized by a different major PostgreSQL version, Postgres will refuse to start. In that case restore from the dump taken in section 3. Only then consider the explicit reset flow in section 10.

### Map tiles

Development uses OpenStreetMap raster tiles. Attribution is required and is shown on the map. Set `VITE_MAP_TILE_URL` and `VITE_MAP_ATTRIBUTION` in `frontend/.env` if you use another public tile source. Do not commit a private tile token.

If tiles fail to load, feature geometry still renders. The Live Map shows a tile-failure banner.

### Seeded demonstration geometry

Zone boundaries, pipeline paths, and asset points are fictional demo sketches around MENA-oriented seed coordinates. They are not live field surveys. Re-running the seed does not randomize or duplicate them.

The Live Network Map route is `/map` (sidebar label: Live Map). Simulated sensor freshness is polled in a single batched request while that page is open.

### Pipeline Lab (water-pipeline-testbed)

`/pipeline-lab` embeds the existing testbed dashboard (FastAPI + Three.js on port 8080). It is **not** rewritten in React. AquaPulse does not own the physics, fault injection, or AIA verdicts.

The testbed simulator defaults to host port 8000, which collides with the AquaPulse API. Start the testbed with the platform overlay so the simulator is published on **8002**:

```bash
cd aquapulse/water-pipeline-testbed
docker compose -f docker-compose.yml -f docker-compose.plateform.yml up --build
```

Then open [http://127.0.0.1:5173/pipeline-lab](http://127.0.0.1:5173/pipeline-lab). Optional: `VITE_TESTBED_URL` in `frontend/.env` (default `http://127.0.0.1:8080`). Vite proxies `/pipeline-lab-proxy` to that dashboard for a same-origin health check. The iframe still loads the dashboard origin so WebSockets and `/static` keep working.

Faults injected in the lab do **not** create AquaPulse incidents, refresh Nokia snapshots, or send valve commands.
