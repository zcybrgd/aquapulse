# Evaluation framework

`run_eval.py` automates the loop the testbed spec asks for:

```
injected scenario -> observed telemetry -> agent investigation -> risk assessment -> expected outcome
```

For each entry in `scenarios.yaml` it:

1. Optionally sets the environment temperature and/or simulates a Nokia NaC
   platform outage for the target cluster.
2. Injects the fault via the simulator's control API.
3. Waits `wait_seconds` for a few AIA batch cycles to run.
4. Fetches the latest recorded result for that cluster from `aia_service`
   (backed by TimescaleDB) and compares its `classification` and
   `severity_tier` against the scenario's expected values.
5. Clears the fault/outage/temperature and resets the simulator's physical
   state before moving to the next scenario, so scenarios that reuse a
   cluster don't inherit leftover drift from the previous one.

Results print live and are written to a JSON report (`--report`, default
`eval_report.json`) with a full breakdown per scenario.

## Running it

Against a `docker compose up` stack:

```bash
pip install -r requirements.txt
python run_eval.py --simulator-url http://localhost:8000 --aia-url http://localhost:8001
```

Exit code is `0` if every scenario passed, `1` otherwise -- safe to drop into CI.

## The eight built-in scenarios

| # | Scenario | Expected classification | Expected tier |
|---|----------|--------------------------|----------------|
| A | Extreme heat + drifting/garbled telemetry, high congestion, unreachable device | `likely_connectivity_artifact` | 1 |
| B | Large leak near the reservoir (highest-criticality segment) | `confirmed_anomaly` | 2–3 |
| C | Hardware sensor failure (flatline), unreachable, low congestion | `confirmed_instrument_fault` | 1 |
| D | Simulated Nokia NaC platform outage during a real leak | `insufficient_data` | 2 (fallback tier) |
| E | Slow pump degradation, moderate-criticality segment | `confirmed_anomaly` | 1–2 |
| F | Valve stuck open (uncontrolled flow) | `confirmed_anomaly` | 1–2 |
| G | Pressure spike (valve closure / surge) | `confirmed_anomaly` | 1–2 |
| H | Sensor drift/miscalibration (no real physical event) | `confirmed_anomaly` | 1–2 |

Note on H: a slowly drifting sensor with no real physical change is, by the
AIA's own design, indistinguishable from a genuine slow anomaly using
telemetry shape alone once it crosses the detection floor -- the AIA has no
way to know the *reported* pressure is fictitious unless CAMARA also reports
a device/network problem (which it doesn't in this scenario, since the
device is perfectly reachable). This is intentionally left as
`confirmed_anomaly` rather than something the agent should be expected to
catch -- it's a useful scenario for illustrating that boundary, not a bug.

## Adding a scenario

Add an entry to `scenarios.yaml`:

```yaml
- name: "My new scenario"
  cluster_id: cluster-desert-046
  env_temp: normal            # optional: normal | high | extreme
  fault_type: pump_failure    # see simulator's /faults/catalog for the full list
  magnitude: default
  simulate_api_outage: false  # optional
  wait_seconds: 12
  expected_classification: confirmed_anomaly
  expected_tier_min: 2
  expected_tier_max: 3
```

New fault *types* (not just magnitudes) are added in
`simulator/app/faults.py`'s `FAULT_LIBRARY` -- see the module docstring
there for the composable `FaultEffect` fields available.
