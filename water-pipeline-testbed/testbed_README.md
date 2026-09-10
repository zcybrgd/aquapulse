# AquaPulse Water Pipeline Testbed

A fully dockerized, GRFICSv3-inspired simulated water distribution network,
wired directly to the already-built **Anomaly Investigation Agent (AIA)**,
with a live web dashboard and an automated scenario-evaluation framework.

```
┌─────────────┐  telemetry batches   ┌──────────────┐   results     ┌───────────┐
│  simulator  │ ───────────────────▶ │  aia-service │──────────────▶│dashboard  │
│ (physics +  │◀───────────────────  │ (wraps the   │   (Redis      │(3D twin + │
│  faults +   │  network_status      │  aia package │    pub/sub)   │ control   │
│  network    │  (CAMARA stand-in)   │  unmodified) │               │ panel +   │
│  sim)       │                      └──────┬───────┘               │ AIA feed) │
└──────┬──────┘                             │                       └───────────┘
       │ sim:state, sim:raw_logs (Redis)    │ writes results                ▲
       └────────────────────────────────────┼───────────────────────────────┘
                                            ▼
                                       TimescaleDB (eval framework reads from here)
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

The UI is split into two clearly separate domains, matching the intended
architecture: the testbed only ever produces **physical simulation** state
and **raw evidence**; the **cybersecurity verdict** always comes from the
Anomaly Investigation Agent, never from the testbed itself.

**Left: Physical Simulation** (the simulated industrial environment)
1. **Start/Stop/Reset** (top bar) control the simulation clock.
2. **3D pipeline view**: a live digital twin — water particles flow through
   each pipe at a speed driven by the real simulated flow rate, pumps spin,
   valve gates react to valve-type faults, and a leak fault produces a
   visible particle spray at the leak point. This is ground-truth physics,
   not a diagnosis — nothing here is colored by severity.
3. **Environment Temperature** (Normal/High/Extreme) drives the shared
   desert ambient temperature, feeding both the physics and the simulated
   cellular network.
4. **Scenario Control Panel**: pick a cluster, fault type, and magnitude,
   then **Inject Fault**. **Simulate NaC Outage** independently fails the
   simulated Nokia NaC platform for the selected cluster.
5. **Raw Sensor Log Stream**: the literal, uninterpreted per-device logs
   (pressure/flow/temperature/connectivity, one line per device) flowing
   out of the simulator — the same evidence the AIA receives. No log line
   here ever says "anomaly" or assigns a severity.
6. **Light/Dark mode**: toggle in the top bar (sun/moon icon). Dark is the
   default; your choice persists across reloads via `localStorage`. Every
   themed color — including status/tier colors — has a dedicated light-mode
   variant tuned for contrast on a light background, not just the dark
   palette reused at lower opacity.

**Right: Cybersecurity Intelligence Layer** (the Anomaly Investigation Agent)
6. **Investigation Feed** populates *only* when the AIA actually produces a
   result for a batch — it starts empty, and injecting a fault does not by
   itself put anything here. Each card shows the agent's classification,
   tier, confidence, the CAMARA network diagnostics it used to disambiguate,
   and its Operator Justification Memo (its reasoning). A small ring
   overlay appears at the corresponding node in the 3D view only once a
   verdict has actually been produced, color-coded by tier/classification —
   the only place a cybersecurity color touches the 3D scene.

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

## Architectural principle: the testbed never decides

This is the most important property of the system, and it's enforced
structurally, not just by convention:

- The simulator's job stops at **Simulate → Measure → Generate telemetry/logs
  → Send logs**. It has no anomaly-detection or alerting code anywhere —
  `simulator/app/raw_logs.py` and `telemetry.py` only ever report literal
  sensor values and device status (`operational` / `stale` / `fault`,
  derived purely from whether *that device's own hardware/comms* is
  working, never from whether the reading "looks wrong").
- Fault injection changes physics and network conditions immediately (so
  the 3D view and raw logs react in real time, as they should — a real
  plant would too), but it never writes a classification anywhere. The
  dashboard's investigation feed and the 3D view's verdict ring are driven
  exclusively by `aia:results` messages published by `aia-service` *after*
  the AIA has actually processed a batch — there is no code path that
  short-circuits from "fault injected" to "alert shown".
- All alert classification (`confirmed_anomaly` + Tier 1/2/3,
  `confirmed_instrument_fault`, `likely_connectivity_artifact`,
  `insufficient_data`) is produced exclusively by the unmodified `aia`
  package. The testbed does not contain a second detection mechanism.

You can verify this yourself: `redis-cli subscribe sim:raw_logs` streams
continuously and immediately on fault injection, while `aia:results` only
appears once the AIA has actually run its 4-stage pipeline on a later
batch — often several seconds afterward, exactly as it would against a
real plant.

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
- **Theming is CSS custom properties, all the way down.** `style.css`
  defines every color as a `--variable` in `:root` (dark, default) with a
  `[data-theme="light"]` override block. Nothing in the rest of the
  stylesheet, `three-scene.js`, or `app.js` hardcodes a color outside those
  two blocks -- switching themes is one attribute flip on `<html>`, applied
  before first paint via a small inline script in `index.html` (so a
  returning visitor who chose light mode never sees a flash of dark). The
  one place a *third* system needed to know about the change is the 3D
  scene's grid lines (baked into GridHelper's vertex colors at construction,
  not a CSS-stylable property), so `three-scene.js` exposes a small
  `setTheme()` that rebuilds just the grid; everything else in the 3D view
  (pipe/pump/valve materials, particles) is a neutral industrial tone that
  reads fine against either background and needs no per-theme change.
