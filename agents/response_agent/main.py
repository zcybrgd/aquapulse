from __future__ import annotations
import argparse
import logging
import sys
import uuid
from .graph import build_actuation_graph
from .schemas import NetworkGrant, SeverityTier
from .tools.actuator_client import ValveActuatorClient
from .tools.notification_client import NotificationClient
from .tools.reachability_client import DeviceReachabilityClient

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",)

class MockReachabilityClient(DeviceReachabilityClient):
    def __init__(self, reachable: bool = True):
        self._reachable = reachable
    def check(self, device_id: str):  # type: ignore[override]
        from .schemas import ReachabilityStatus
        return ReachabilityStatus(device_id=device_id, reachable=self._reachable, raw_signal_quality="good")
class MockNotificationClient(NotificationClient):
    def __init__(self):
        pass
    def send(self, recipient, message, channel="sms", incident_id=None) -> bool:  # type: ignore[override]
        print(f"  [NOTIFY:{channel}] to={recipient} -> {message}")
        return True


class MockActuatorClient(ValveActuatorClient):
    def __init__(self, should_confirm: bool = True):
        self._should_confirm = should_confirm
    def isolate(self, device_id, incident_id) -> bool:  # type: ignore[override]
        print(f"  [ACTUATOR] closing valve on device={device_id} incident={incident_id}")
        if not self._should_confirm:
            from .tools.actuator_client import ValveCommandError
            raise ValveCommandError("mock actuator failed to confirm closure")
        return True


SCENARIOS = {"tier1": dict(tier=SeverityTier.TIER_1_MONITOR, reachable=True),"tier2": dict(tier=SeverityTier.TIER_2_ALERT, reachable=True),
"tier3": dict(tier=SeverityTier.TIER_3_AUTONOMOUS, reachable=True),"unreachable": dict(tier=SeverityTier.TIER_3_AUTONOMOUS, reachable=False),
"actuator_failure": dict(tier=SeverityTier.TIER_3_AUTONOMOUS, reachable=True, actuator_fails=True),}


def run_scenario(name: str) -> None:
    if name not in SCENARIOS:
        print(f"Unknown scenario '{name}'. Options: {list(SCENARIOS)}")
        sys.exit(1)
    cfg = SCENARIOS[name]
    incident_id = str(uuid.uuid4())
    cluster_id = "cluster-14"
    device_id = "device-14-valve-A"
    print(f"\n=== Running scenario: {name} (tier={int(cfg['tier'])}) ===")
    app = build_actuation_graph(reachability_client=MockReachabilityClient(reachable=cfg["reachable"]),notification_client=MockNotificationClient(),
    actuator_client=MockActuatorClient(should_confirm=not cfg.get("actuator_fails", False)),audit_sink=lambda entry: print(f"  [AUDIT] {entry.model_dump_json(indent=2)}"),
    override_poller=lambda incident_id: "confirmed",  # instant confirm for demo
    override_window_seconds=5.0,)
    initial_state = {"incident_id": incident_id,"cluster_id": cluster_id,"device_id": device_id,"severity_tier": cfg["tier"],
        "network_grant": NetworkGrant(cluster_id=cluster_id,incident_id=incident_id,severity_tier=cfg["tier"],guarantee_type="QoD",session_id=str(uuid.uuid4()),),
        "operator_contact": "+15550001234","reasoning_trace": [],}
    final_state = app.invoke(initial_state)
    print("\n--- Reasoning trace ---")
    for line in final_state["reasoning_trace"]:
        print(f"  - {line}")
    print(f"\nFinal decision: {final_state['decision']}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Actuation & Audit Agent demo scenarios.")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS))    
    parser.add_argument("--live", action="store_true", help="Use the real camara-integration service instead of mocks")                                                  
    args = parser.parse_args()
    run_scenario(args.scenario) 