# Anomaly Investigation Agent (AIA)

Implementation of the AquaPulse **Anomaly Investigation Agent** per
*Technical Specification v4.0 (Production-Ready MVP Specification)*.

The AIA is a 4-stage pipeline that ingests raw pipeline telemetry, filters
it with cheap deterministic + ML checks, actively investigates the
survivors against Nokia NaC CAMARA APIs to disambiguate physical leaks from
network artifacts, computes safety-critical risk tiers in pure Python, and
uses an LLM **only** as a read-only narrator.

```
Raw batch --> Stage 1: Detection --> Stage 2: Investigation --> Stage 3: Risk --> Stage 4: Narration --> NMA
              (Z-score + IsoForest)   (CAMARA disambiguation)   (deterministic)   (LLM, read-only)
```

## Project layout

```
aia/
  config.py         All safety-critical thresholds/weights in one auditable place
  models.py         Pydantic v2 schemas for input, output, and internal state
  detection.py       Stage 1: Z-score safety floors + Isolation Forest (temperature-adaptive)
  camara_client.py   Nokia NaC CAMARA client (Mock + HTTP implementations), try/except wrapping
  investigation.py   Stage 2: reachability/congestion disambiguation, retry/escalation
  risk.py             Stage 3: hydraulic trend calc, severity tiering, confidence score
  narration.py        Stage 4: LLM narrator (Anthropic) + deterministic fallback
  topology.py         Local fast-lookup pipeline topology cache (in-memory + Redis)
  storage.py           TimescaleDB archival for healthy telemetry (in-memory + Postgres)
  graph.py              LangGraph orchestrator wiring Stages 2-4 per suspicious cluster
  pipeline.py            Batch-level orchestrator: Stage 1 fan-out, cross-batch retry tracking,
                          output payload compilation
  main.py                 Runnable example reproducing the spec's sample batch end-to-end
tests/
  test_detection.py, test_investigation.py, test_risk.py   Unit tests per stage
  test_scenarios.py                                          Scenarios A-E from spec Section 9
```

## Running it

```bash
pip install -r requirements.txt
python -m aia.main          # runs the spec's example batch, prints the output payload
python -m pytest tests/ -v  # 20 tests, including all 5 target simulation scenarios
```

## Design decisions worth knowing about

- **Deterministic-first.** All Z-score checks, hydraulic slope/trend math,
  criticality lookups, severity tiering, and the confidence score are pure
  Python/NumPy (`detection.py`, `risk.py`). The LLM in `narration.py` never
  sees raw telemetry math — only the already-computed classification, tier,
  and metrics, and it is explicitly instructed not to alter them.
- **Safety Separation Rule.** Temperature-adaptive noise tolerance is applied
  *only* to the Isolation Forest decision boundary in `detection.py`. The
  Z-score threshold and the sharp-deviation floors are never temperature
  adjusted, so extreme heat can't be used to mask a real leak.
- **API failures never become inferences.** `camara_client.py`'s
  `safe_get_*` wrappers catch every exception and turn it into
  `api_unavailable=True`; `investigation.py` routes that straight to
  `insufficient_data` rather than guessing UNREACHABLE/HIGH-congestion.
- **Insufficient-data still gets reported.** Per Section 8's Actionable
  Interpretation Matrix, an `insufficient_data` cluster is *both* included
  in the current batch's output (with the Section-8 fallback tier, so the
  NMA can trigger its safety fallback) *and* re-queued for the next cycle.
  `pipeline.RetryTracker` keeps the consecutive-cycle count across
  `process_batch()` calls and marks `escalate_to_human=True` on the 3rd
  consecutive cycle (Scenario E).
- **Prompt-injection guardrail.** `models.sanitize_identifier()` is enforced
  as a Pydantic field validator on every field-sourced identifier
  (`sensor_cluster_id`, `segment_id`, `associated_valve_id`) at ingestion
  time, and re-checked defensively in `narration.py` before any identifier
  enters the LLM prompt.
- **Topology-cache miss is treated conservatively.** If a cluster has no
  topology mapping, `risk.assign_segment_metadata` assigns criticality 3
  rather than defaulting low — an unknown asset should never be silently
  downgraded.
- **Everything external is swappable.** `CamaraClient`, `TopologyCache`, and
  `TelemetryStore` are `Protocol`s with both in-memory (test/demo) and real
  (Redis / TimescaleDB / HTTP CAMARA sandbox) implementations, so the same
  pipeline code runs in tests and in production. `anthropic_client` is
  injected too — pass `None` to use the deterministic template narrator, or
  an `anthropic.Anthropic()` instance for live LLM narration
  (`ANTHROPIC_API_KEY` env var).
