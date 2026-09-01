from __future__ import annotations
import uuid
import pytest
from pydantic import ValidationError
from response_agent.graph import build_actuation_graph
from response_agent.schemas import (ActuationDecision,ActuationResult,NetworkGrant,ReachabilityStatus,SeverityTier,)
from response_agent.tools.actuator_client import ValveCommandError
# Fakes simple, deterministic stand-ins for the real HTTP

class FakeReachabilityClient:
    def __init__(self, reachable: bool):
        self._reachable = reachable
    def check(self, device_id: str) -> ReachabilityStatus:
        return ReachabilityStatus(device_id=device_id, reachable=self._reachable)


class FakeNotificationClient:
    def __init__(self):
        self.sent_messages: list[dict] = []
    def send(self, recipient, message, channel="sms", incident_id=None) -> bool:
        self.sent_messages.append( {"recipient": recipient, "message": message, "channel": channel, "incident_id": incident_id} )
        return True


class FakeActuatorClient:
    def __init__(self, should_confirm: bool = True):
        self._should_confirm = should_confirm
        self.isolate_calls: list[tuple[str, str]] = []
    def isolate(self, device_id: str, incident_id: str) -> bool:
        self.isolate_calls.append((device_id, incident_id))
        if not self._should_confirm:
            raise ValveCommandError("mock: actuator did not confirm closure")
        return True


def make_initial_state(tier: SeverityTier, cluster_id="cluster-1", device_id="device-1"):
    incident_id = str(uuid.uuid4())
    return { "incident_id": incident_id,"cluster_id": cluster_id,"device_id": device_id,"severity_tier": tier,
    "network_grant": NetworkGrant(cluster_id=cluster_id,incident_id=incident_id,severity_tier=tier,guarantee_type="QoD",session_id=str(uuid.uuid4()),),"operator_contact": "+15550001234","reasoning_trace": [],}


def build_test_graph(reachable=True, actuator_confirms=True, override_response="confirmed"):
    audit_entries = []
    graph = build_actuation_graph( reachability_client=FakeReachabilityClient(reachable=reachable),notification_client=(notifier := FakeNotificationClient()),actuator_client=(actuator := FakeActuatorClient(should_confirm=actuator_confirms)),audit_sink=lambda entry: audit_entries.append(entry),override_poller=lambda incident_id: override_response,override_window_seconds=1.0,poll_interval_seconds=0.01,)
    return graph, notifier, actuator, audit_entries

# Tier logic
def test_tier1_logs_only_no_notification_no_valve():
    graph, notifier, actuator, audit_entries = build_test_graph()
    state = make_initial_state(SeverityTier.TIER_1_MONITOR)
    result = graph.invoke(state)
    assert result["decision"] == ActuationDecision.LOG_ONLY
    assert notifier.sent_messages == []
    assert actuator.isolate_calls == []
    assert len(audit_entries) == 1


def test_tier2_alerts_operator_but_never_touches_valve():
    graph, notifier, actuator, audit_entries = build_test_graph()
    state = make_initial_state(SeverityTier.TIER_2_ALERT)
    result = graph.invoke(state)
    assert result["decision"] == ActuationDecision.ALERT_AND_AWAIT
    assert len(notifier.sent_messages) == 1
    assert actuator.isolate_calls == []  # never autonomous at Tier 2


def test_tier3_isolates_valve_and_notifies_simultaneously():
    graph, notifier, actuator, audit_entries = build_test_graph(override_response="confirmed")
    state = make_initial_state(SeverityTier.TIER_3_AUTONOMOUS)
    result = graph.invoke(state)
    assert result["decision"] == ActuationDecision.AUTONOMOUS_ISOLATE
    assert result["valve_command_confirmed"] is True
    assert len(actuator.isolate_calls) == 1
    assert len(notifier.sent_messages) == 1
    assert result["human_override_requested"] is True
    assert result["human_override_response"] == "confirmed"

# Safety guardrails

def test_unreachable_device_blocks_action_regardless_of_tier():
    """The core reachability guardrail: even a Tier 3 event must not
    autonomously fire a valve command if the device can't be confirmed
    reachable."""
    graph, notifier, actuator, audit_entries = build_test_graph(reachable=False)
    state = make_initial_state(SeverityTier.TIER_3_AUTONOMOUS)
    result = graph.invoke(state)
    assert result["decision"] == ActuationDecision.ESCALATE_UNREACHABLE
    assert actuator.isolate_calls == []  # never fires blind
    assert len(notifier.sent_messages) == 1  # but always tells a human


def test_valve_command_failure_escalates_instead_of_retrying():
    graph, notifier, actuator, audit_entries = build_test_graph( actuator_confirms=False, override_response="confirmed")
    state = make_initial_state(SeverityTier.TIER_3_AUTONOMOUS)
    result = graph.invoke(state)
    assert result["valve_command_sent"] is True
    assert result["valve_command_confirmed"] is False
    # exactly one isolate attempt — no blind retry loop
    assert len(actuator.isolate_calls) == 1
    # two notifications: the initial Tier 3 alert + the emergency escalation
    assert len(notifier.sent_messages) == 2
    assert "FAILED" in notifier.sent_messages[-1]["message"]


def test_severity_tier_ceiling_is_enforced_by_schema():
    """ActuationResult must refuse any tier above the defined ceiling —
    this is the last line of defense against an upstream bug."""
    with pytest.raises(ValidationError):
        ActuationResult(incident_id="x",cluster_id="x",device_id="x",severity_tier=4,  reachability=ReachabilityStatus(device_id="x", reachable=True),decision=ActuationDecision.LOG_ONLY,)

# Human override window

def test_human_override_can_reverse_autonomous_action():
    graph, notifier, actuator, audit_entries = build_test_graph(override_response="overridden")
    state = make_initial_state(SeverityTier.TIER_3_AUTONOMOUS)
    result = graph.invoke(state)
    assert result["human_override_response"] == "overridden"
    assert len(actuator.isolate_calls) == 1


def test_human_override_times_out_when_no_response_arrives():
    graph = build_actuation_graph(reachability_client=FakeReachabilityClient(reachable=True),notification_client=FakeNotificationClient(),actuator_client=FakeActuatorClient(should_confirm=True),audit_sink=lambda entry: None,override_poller=lambda incident_id: None,  override_window_seconds=1.0,poll_interval_seconds=0.01,)
    state = make_initial_state(SeverityTier.TIER_3_AUTONOMOUS)
    result = graph.invoke(state)
    assert result["human_override_response"] == "timed_out"
    assert any("closed without a response" in line for line in result["reasoning_trace"])

# Audit trail
def test_audit_entry_captures_full_decision_chain():
    graph, notifier, actuator, audit_entries = build_test_graph()
    state = make_initial_state(SeverityTier.TIER_2_ALERT)
    graph.invoke(state)
    assert len(audit_entries) == 1
    entry = audit_entries[0]
    assert entry.actuation_result.decision == ActuationDecision.ALERT_AND_AWAIT
    assert entry.network_grant is not None
    assert entry.severity_tier == SeverityTier.TIER_2_ALERT

def test_reasoning_trace_is_non_empty_and_ordered():
    graph, notifier, actuator, audit_entries = build_test_graph()
    state = make_initial_state(SeverityTier.TIER_1_MONITOR)
    result = graph.invoke(state)
    assert len(result["reasoning_trace"]) >= 2  # reachability + execution
    assert "reachable" in result["reasoning_trace"][0].lower()

"""
Test suite for the Actuation & Audit Agent.

Covers:
  - deterministic tier -> action mapping (Tier 1/2/3)
  - the hard safety ceiling (never process above Tier 3)
  - the unreachable-device override (never act on an unreachable device,
    regardless of tier)
  - the valve-command failure fallback (escalate, don't retry blindly)
  - the human override window (confirmed / overridden / timed out)
  - schema validation edge cases

Run with:  pytest -v
"""
