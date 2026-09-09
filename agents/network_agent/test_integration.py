from __future__ import annotations
import argparse
import json
import logging
import sys
import uuid
from typing import Any, Dict, List

from agents.network_agent.graph import graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("network_agent.test_integration")
DEVICE_ID = "+99999991001"
CLUSTER_ID = "cluster-14"


def _make_threat(
    *,
    incident_id: str,
    severity_tier: int,
    criticality_score: int,
    confidence: float,
    device_id: str = DEVICE_ID,
    cluster_id: str = CLUSTER_ID,
    network_degradation: bool = False,
) -> Dict[str, Any]:
    """Builds a full InvestigatedThreat dict matching schemas.py exactly."""
    return {
        "anomaly_id": incident_id,
        "sensor_cluster_id": cluster_id,
        "segment_id": "segment-A",
        "device_id": device_id,
        "classification": "CONFIRMED_LEAK",
        "severity_tier": severity_tier,
        "network_status": {
            "device_online": True,
            "device_reachable": True,
            "network_degradation_detected": network_degradation,
            "camara_device_status": "CONNECTED_SMS",
            "camara_reachability_status": "REACHABLE",
        },
        "physical_deviations": {
            "pressure_drop_pct": 42.5,
            "flow_surge_pct": 18.2,
            "pressure_slope": -3.1,
            "flow_slope": 2.4,
        },
        "criticality_metrics": {
            "criticality_score": criticality_score,
            "proximity_to_reservoir_m": 120.0,
            "population_served": 5000,
            "associated_valve_id": device_id,
        },
        "operator_justification": "Sharp pressure drop with confirmed flow surge near reservoir.",
        "confidence_score": confidence,
    }


SCENARIOS = {
    "qod": lambda: [
        _make_threat(
            incident_id=f"incident-{uuid.uuid4()}",
            severity_tier=2,
            criticality_score=3,
            confidence=0.85,
        )
    ],
    "slice": lambda: [
        _make_threat(
            incident_id=f"incident-{uuid.uuid4()}",
            severity_tier=3,
            criticality_score=5,
            confidence=0.97,
            device_id="+99999991000",
            network_degradation=True,
        ),
        _make_threat(
            incident_id=f"incident-{uuid.uuid4()}",
            severity_tier=3,
            criticality_score=5,
            confidence=0.95,
            device_id="+99999991003",
            network_degradation=True,
        ),
    ],
    "deny": lambda: [
        _make_threat(
            incident_id=f"incident-{uuid.uuid4()}",
            severity_tier=1,
            criticality_score=1,
            confidence=0.5,
        )
    ],
}


def run_scenario(name: str) -> None:
    if name not in SCENARIOS:
        print(f"Unknown scenario '{name}'. Options: {list(SCENARIOS)}")
        sys.exit(1)

    threats: List[Dict[str, Any]] = SCENARIOS[name]()
    incident_ids = [t["anomaly_id"] for t in threats]

    print(f"\n=== Running network-agent integration scenario: {name} ===")
    print(f"    incident_id(s): {incident_ids}")

    initial_input = {"raw_requests": threats, "messages": []}

    final_state = None
    for chunk in graph.stream(initial_input, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            if node_output is None:
                print(f"\n---- [ NODE: {node_name} ] ---- (no state update)")
                continue
            print(f"\n---- [ NODE: {node_name} ] ----")
            for key, val in node_output.items():
                if key != "messages":
                    print(f"  {key}: {val}")
            if node_output.get("messages"):
                for msg in node_output["messages"]:
                    msg.pretty_print()
            final_state = node_output

    print("\n=== Network agent graph finished ===")
    print(
        "Check the log lines above/below for 'dispatch_node_complete' to confirm "
        "the bridge fired, then look for 'reachability_check_node', "
        "'llm_decision_node', 'execute_response_node', 'release_network_node', "
        "and 'audit_writer_node' — these run in-process via the dispatch thread "
        "pool and may print slightly after the graph.stream() loop above ends."
    )
    print(
        f"\nFor incident(s) {incident_ids}: if this was the 'slice' scenario, "
        "the response agent invocation happens later via the webhook_server "
        "lifecycle watcher (terminal running webhook_server:app), not here — "
        "watch that terminal for PENDING -> AVAILABLE -> OPERATING."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the Network Agent -> Response Agent integration end to end."
    )
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS))
    args = parser.parse_args()
    run_scenario(args.scenario)