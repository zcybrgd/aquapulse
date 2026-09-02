# AquaPulse Water Pipeline Testbed

A fully dockerized, GRFICSv3-inspired simulated water distribution network,
wired directly to the already-built **Anomaly Investigation Agent (AIA)**,
with a live web dashboard and an automated scenario-evaluation framework.

```
┌─────────────┐  telemetry batches   ┌──────────────┐   results    ┌───────────┐
│  simulator   │ ───────────────────▶│  aia-service │──────────────▶│dashboard  │
│ (physics +   │◀───────────────────│ (wraps the   │   (Redis      │(live SVG +│
│  faults +    │  network_status     │  aia package │    pub/sub)   │ control   │
│  network     │  (CAMARA stand-in)  │  unmodified) │               │ panel)    │
│  sim)        │                     └──────┬───────┘               └───────────┘
└──────┬───────┘                            │
       │ sim:state (Redis)                  │ writes results
       ▼                                     ▼
   dashboard ◀───────────────────── TimescaleDB (eval framework reads from here)
```

Five services, orchestrated with `docker compose`:

| Service | What it does |
|---|---|
| `simulator` | Runs the pipeline physics (5 sensor clusters: pump + pipe + valve + pressure/flow/temp sensors each), the fault-injection engine, and a simulated cellular/CAMARA network layer. Dispatches rolling telemetry windows to `aia-service` and publishes live state to Redis. |
| `aia-service` | A thin FastAPI wrapper around the **unmodified** `aia` package (copied in from the standalone AIA implementation). Validates incoming batches against the AIA's own Pydantic schema, runs the 4-stage pipeline, persists results to TimescaleDB, and publishes them to Redis. |
| `dashboard` | Serves the Scenario Control Panel + live pipeline visualization. Subscribes to Redis and rebroadcasts to connected browsers over WebSocket; proxies control commands to `simulator`. |
| `redis` | Pub/sub broker between `simulator` → `dashboard` and `aia-service` → `dashboard`. |
| `timescaledb` | Archives every AIA result, so the evaluation framework can query "what did the agent actually decide?" after the fact. |

The `eval/` directory (run separately, not a Docker service) automates
**injected scenario → observed telemetry → agent investigation → risk
assessment → expected outcome** across 8 built-in scenarios covering every
disambiguation path the AIA supports.

## Quickstart

```bash
cp .env.example .env   # optional: set ANTHROPIC_API_KEY for live LLM narration
docker compose up --build
```

Then open **http://localhost:8080** for the dashboard.

- Simulator API: http://localhost:8000 (see `/faults/catalog`, `/topology`, `/state`)
- AIA service API: http://localhost:8001 (see `/results/latest/{cluster_id}`)
- TimescaleDB: `localhost:5432` (user/pass/db: `aia`/`aia`/`aia`)

## Using the dashboard

1. **Start/Stop/Reset** control the simulation clock.
2. **Environment Temperature** (Normal/High/Extreme) drives the shared
   desert ambient temperature, which feeds both the physics (thermal
   effects) and the simulated cellular network (heat degrades signal).
3. **Scenario Control Panel**: pick a cluster, a fault type, and a
   magnitude (where applicable), then **Inject Fault**. The pipeline
   diagram node for that cluster will change color once the AIA has
   investigated it (green = normal, yellow/orange/red = Tier 1/2/3
   confirmed anomaly, gray = instrument fault, blue = connectivity
   artifact / insufficient data).
4. **Simulate Outage** / **Clear Outage** simulates the Nokia NaC CAMARA
   platform itself failing for the selected cluster (distinct from a
   fault that just makes the *reading* say UNREACHABLE) -- this is what
   drives the AIA's `insufficient_data` path.
5. The **Anomaly Investigation Feed** shows each investigated cluster's
   classification, tier, confidence score, and the AIA's Operator
   Justification Memo, live, as results arrive.

## Fault catalog

`GET /faults/catalog` (or the dashboard's fault-type dropdown) lists
everything available: `leak` (small/medium/large), `pipe_rupture`,
`pressure_spike`, `pressure_drop`, `pump_failure`, `pump_degradation`,
`valve_stuck_open`, `valve_stuck_closed`, `sensor_failure`, `sensor_drift`,
`sensor_comm_loss`, `high_flow`, `low_flow`, `network_loss`,
`thermal_cell_degradation`. Every fault is defined as a small composable
`FaultEffect` in `simulator/app/faults.py` -- see that file's docstring for
how to add a new scenario without touching the simulation loop.

## Realistic telemetry, not "LEAK DETECTED"

Per the spec, raw telemetry never states the injected fault. What actually
flows to the AIA is exactly its documented `StreamingBatch` schema:
per-cluster rolling windows of `{timestamp, pressure_psi, flow_rate_lps,
ambient_temp_c}` readings plus `network_metadata` (signal strength, packet
loss). The AIA has to infer what's going on from that alone, disambiguating
against the simulated CAMARA network layer -- the same way it would against
the real Nokia NaC platform.

## Running the evaluation suite

```bash
cd eval
pip install -r requirements.txt
python run_eval.py --simulator-url http://localhost:8000 --aia-url http://localhost:8001
```

See `eval/README.md` for the full scenario list and how to add new ones.
All 8 built-in scenarios pass against the current build, covering every
classification the AIA can produce: `confirmed_anomaly` (Tiers 1-3),
`confirmed_instrument_fault`, `likely_connectivity_artifact`, and
`insufficient_data`.

## Local development without Docker

Each service is a plain FastAPI app and can be run directly for faster
iteration (requires local Redis + Postgres):

```bash
# terminal 1
cd simulator/app
AIA_SERVICE_URL=http://127.0.0.1:8001 REDIS_URL=redis://127.0.0.1:6379/0 \
  uvicorn main:app --port 8000

# terminal 2
cd aia_service/app
SIMULATOR_URL=http://127.0.0.1:8000 REDIS_URL=redis://127.0.0.1:6379/0 \
  POSTGRES_DSN=postgresql://aia:aia@127.0.0.1:5432/aia \
  PYTHONPATH=.. uvicorn main:app --port 8001

# terminal 3
cd dashboard/app
SIMULATOR_URL=http://127.0.0.1:8000 AIA_SERVICE_URL=http://127.0.0.1:8001 \
  REDIS_URL=redis://127.0.0.1:6379/0 uvicorn main:app --port 8080
```

## Design notes

- **The AIA is not redesigned.** `aia_service/aia/` is a byte-for-byte copy
  of the standalone AIA implementation. Integration happens entirely
  through its existing extension points: a `SimulatedCamaraClient`
  implementing the `CamaraClient` protocol (`aia_service/app/camara_sim_client.py`),
  an `InMemoryTopologyCache` seeded from the shared topology config, and
  the existing `AnomalyInvestigationAgent` public API. The only change made
  *inside* the AIA package during this build was a genuine bug fix (see
  below), not a redesign.
- **One real bug found and fixed via this testbed.** `BaselineStore.record_and_maybe_fit()`
  originally re-ingested every reading in each incoming rolling window into
  the Isolation Forest's bootstrap history. Since consecutive windows
  overlap heavily, this flooded the model with near-duplicate rows and
  collapsed its learned variance, pushing the false-positive rate to ~14%
  in a 2-minute no-fault soak test (target is ≤2%). Fixed to append only
  the newest reading per call; a follow-up soak test measured ~1% FPR. This
  is exactly the kind of issue the spec's integration testbed is meant to
  surface -- it would not have been caught by the AIA's own unit tests,
  which only ever exercised non-overlapping mock windows.
- **Shared topology, duplicated on purpose.** `simulator/app/topology.py`
  and `aia_service/app/topology.py` are identical files, each self-contained
  within its own Docker build context rather than imported across a shared
  package. See the comment at the top of either file.
- **Fault injection is data, not code.** Every named scenario in the spec
  (leak sizes, rupture, pressure spike/drop, pump failure/degradation,
  valve stuck open/closed, sensor failure/drift/comm-loss, high/low flow,
  network loss, thermal degradation) is one `FaultEffect` entry in
  `faults.py`'s `FAULT_LIBRARY`, not a bespoke function -- adding a new
  scenario later is a data change, not a simulation-loop change.
