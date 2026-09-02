from __future__ import annotations
import argparse
import logging
import sys
import uuid

from .graph import build_actuation_graph
from .nodes.llm_response_planner import build_llm_decision_chain
from .schemas import NetworkGrant, SeverityTier
from .tools.actuator_client import ValveActuatorClient
from .tools.notification_client import NotificationClient
from .tools.reachability_client import DeviceReachabilityClient

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",)
logger = logging.getLogger("actuation_agent.main")

# device_id must exist in camara-integration's DEVICE_ID_MAP
SCENARIOS = {
    "tier1": dict(tier=SeverityTier.TIER_1_MONITOR, device_id="device-14-valve-A"),
    "tier2": dict(tier=SeverityTier.TIER_2_ALERT, device_id="device-14-valve-A"),
    "tier3": dict(tier=SeverityTier.TIER_3_AUTONOMOUS, device_id="device-14-valve-A"),
    "unreachable": dict(tier=SeverityTier.TIER_3_AUTONOMOUS, device_id="device-offline-demo"),
    "actuator_failure": dict(tier=SeverityTier.TIER_3_AUTONOMOUS, device_id="device-14-valve-A-fail"),
}


def run_scenario( name: str, reachability_url: str, notification_url: str,actuator_url: str, override_seconds: float,) -> None:
    if name not in SCENARIOS:
        print(f"Unknown scenario '{name}'. Options: {list(SCENARIOS)}")
        sys.exit(1)
    cfg = SCENARIOS[name]
    incident_id = str(uuid.uuid4())
    cluster_id = "cluster-14"
    device_id = cfg["device_id"]
    tier = cfg["tier"]
    print(f"\n=== Running scenario: {name} (tier={int(tier)}, device={device_id}) ===")
    reachability_client = DeviceReachabilityClient(base_url=reachability_url)
    notification_client = NotificationClient(base_url=notification_url)
    actuator_client = ValveActuatorClient(base_url=actuator_url)
    llm_chain = build_llm_decision_chain()
    app = build_actuation_graph(reachability_client=reachability_client,notification_client=notification_client,
        actuator_client=actuator_client,llm_chain=llm_chain,
        audit_sink=lambda entry: print(f"  [AUDIT] {entry.model_dump_json(indent=2)}"),
        override_poller=lambda incident_id: "confirmed",override_window_seconds=override_seconds,)

    initial_state = {"incident_id": incident_id,"cluster_id": cluster_id,"device_id": device_id,"severity_tier": tier,
    "network_grant": NetworkGrant( cluster_id=cluster_id, incident_id=incident_id,severity_tier=tier,guarantee_type="QoD", session_id=str(uuid.uuid4()),),"operator_contact": "+15550001234","reasoning_trace": [],}

    final_state = app.invoke(initial_state)

    print("\n--- Reasoning trace ---")
    for line in final_state["reasoning_trace"]:
        print(f"  - {line}")
    print(f"\nOperator message: {final_state.get('operator_message')}")
    print(f"Final decision: {final_state['decision']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Response Agent against live services.")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS))
    parser.add_argument("--reachability-url", default="http://localhost:8001")
    parser.add_argument("--notification-url", default="http://localhost:8002")
    parser.add_argument("--actuator-url", default="http://localhost:8003")
    parser.add_argument("--override-window", type=float, default=15.0)
    args = parser.parse_args()
    run_scenario(name=args.scenario, reachability_url=args.reachability_url,notification_url=args.notification_url,actuator_url=args.actuator_url,override_seconds=args.override_window, )