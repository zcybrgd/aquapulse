"""
Evaluation framework for the AquaPulse testbed (Section 6 of the testbed
spec): for every injected scenario in `scenarios.yaml`, this script

    injected scenario -> observed telemetry -> agent investigation ->
    risk assessment -> expected outcome

and reports a pass/fail comparison, so the AIA's behavior can be validated
against ground truth systematically rather than by eyeballing the dashboard.

Usage:
    python run_eval.py [--simulator-url URL] [--aia-url URL] [--scenarios PATH]

Requires the simulator and aia_service to already be running (e.g. via
`docker compose up`, or the local dev setup in the top-level README).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
import yaml


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    expected_classification: str
    actual_classification: str | None
    expected_tier_range: tuple[int | None, int | None]
    actual_tier: int | None
    confidence_score: float | None
    notes: str = ""


def load_scenarios(path: str) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)


def run_scenario(client: httpx.Client, simulator_url: str, aia_url: str, scenario: dict) -> ScenarioResult:
    cluster_id = scenario["cluster_id"]
    name = scenario["name"]

    # 1. Set environment temperature, if specified.
    if scenario.get("env_temp"):
        client.post(f"{simulator_url}/control/set_temperature", json={"preset": scenario["env_temp"]})

    # 2. Simulated Nokia NaC platform outage, if this scenario calls for it.
    if scenario.get("simulate_api_outage"):
        client.post(f"{simulator_url}/control/simulate_api_outage/{cluster_id}")

    # 3. Inject the fault.
    marker_ts = datetime.now(timezone.utc).isoformat()
    resp = client.post(
        f"{simulator_url}/control/inject_fault",
        json={
            "cluster_id": cluster_id,
            "fault_type": scenario["fault_type"],
            "magnitude": scenario.get("magnitude", "default"),
        },
    )
    if resp.status_code >= 400:
        return ScenarioResult(
            name=name, passed=False,
            expected_classification=scenario["expected_classification"],
            actual_classification=None,
            expected_tier_range=(scenario.get("expected_tier_min"), scenario.get("expected_tier_max")),
            actual_tier=None, confidence_score=None,
            notes=f"inject_fault failed: {resp.text[:200]}",
        )

    # 4. Wait for the AIA to process a few batches.
    time.sleep(scenario.get("wait_seconds", 10))

    # 5. Fetch the latest result for this cluster and compare.
    result = None
    try:
        r = client.get(f"{aia_url}/results/latest/{cluster_id}")
        if r.status_code == 200:
            result = r.json()
    except Exception as exc:  # noqa: BLE001
        pass

    # 6. Clean up: clear the fault and any simulated outage before the next scenario.
    client.post(f"{simulator_url}/control/clear_fault/{cluster_id}")
    if scenario.get("simulate_api_outage"):
        client.post(f"{simulator_url}/control/clear_api_outage/{cluster_id}")
    if scenario.get("env_temp"):
        client.post(f"{simulator_url}/control/set_temperature", json={"preset": "normal"})

    exp_class = scenario["expected_classification"]
    exp_tier_min = scenario.get("expected_tier_min")
    exp_tier_max = scenario.get("expected_tier_max")

    if result is None:
        return ScenarioResult(
            name=name, passed=False, expected_classification=exp_class,
            actual_classification=None, expected_tier_range=(exp_tier_min, exp_tier_max),
            actual_tier=None, confidence_score=None,
            notes="No AIA result recorded for this cluster within the wait window.",
        )

    actual_class = result.get("classification")
    actual_tier = result.get("severity_tier")
    confidence = result.get("confidence_score")

    class_ok = actual_class == exp_class
    tier_ok = True
    if exp_tier_min is not None:
        tier_ok = tier_ok and (actual_tier is not None and actual_tier >= exp_tier_min)
    if exp_tier_max is not None:
        tier_ok = tier_ok and (actual_tier is not None and actual_tier <= exp_tier_max)

    return ScenarioResult(
        name=name, passed=class_ok and tier_ok,
        expected_classification=exp_class, actual_classification=actual_class,
        expected_tier_range=(exp_tier_min, exp_tier_max), actual_tier=actual_tier,
        confidence_score=confidence,
        notes="" if (class_ok and tier_ok) else "classification or tier mismatch",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator-url", default="http://localhost:8000")
    parser.add_argument("--aia-url", default="http://localhost:8001")
    parser.add_argument("--scenarios", default="scenarios.yaml")
    parser.add_argument("--report", default="eval_report.json", help="Path to write the JSON report")
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenarios)
    results: list[ScenarioResult] = []

    with httpx.Client(timeout=10.0) as client:
        # Make sure we're starting from a clean slate.
        client.post(f"{args.simulator_url}/control/reset")
        time.sleep(2)

        for scenario in scenarios:
            print(f"\n=== Running: {scenario['name']} ===")
            # Full physics reset before each scenario, not just at the start of the
            # whole run -- scenarios reuse clusters, and only the *fault* is cleared
            # between scenarios (not the true pressure/flow state it left behind),
            # so without this a fast/large fault in one scenario can leave the next
            # scenario's cluster starting from an already-degraded baseline.
            client.post(f"{args.simulator_url}/control/reset")
            time.sleep(2)
            result = run_scenario(client, args.simulator_url, args.aia_url, scenario)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(
                f"[{status}] expected={result.expected_classification} "
                f"(tier {result.expected_tier_range}) | "
                f"actual={result.actual_classification} (tier {result.actual_tier}, "
                f"confidence={result.confidence_score}) {('- ' + result.notes) if result.notes else ''}"
            )
            time.sleep(2)

        client.post(f"{args.simulator_url}/control/reset")

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 72)
    print(f"EVALUATION SUMMARY: {passed}/{total} scenarios passed")
    print("=" * 72)
    for r in results:
        print(f"  [{'PASS' if r.passed else 'FAIL'}] {r.name}")

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "total": total,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "expected_classification": r.expected_classification,
                "actual_classification": r.actual_classification,
                "expected_tier_range": r.expected_tier_range,
                "actual_tier": r.actual_tier,
                "confidence_score": r.confidence_score,
                "notes": r.notes,
            }
            for r in results
        ],
    }
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written to {args.report}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
