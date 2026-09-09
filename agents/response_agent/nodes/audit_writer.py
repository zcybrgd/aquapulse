from __future__ import annotations
import logging
from typing import Callable
from ..schemas import ActuationResult, AuditLogEntry
from ..state import ActuationState
logger = logging.getLogger("actuation_agent.nodes.audit_writer")
AuditSink = Callable[[AuditLogEntry], None]


def make_audit_writer_node(sink: AuditSink):
    def audit_writer_node(state: ActuationState) -> ActuationState:
        result = ActuationResult(incident_id=state["incident_id"],cluster_id=state["cluster_id"],device_id=state["device_id"],severity_tier=state["severity_tier"],reachability=state["reachability"],decision=state["decision"],notification_sent=state.get("notification_sent", False),valve_command_sent=state.get("valve_command_sent", False),valve_command_confirmed=state.get("valve_command_confirmed", False),human_override_requested=state.get("human_override_requested", False),human_override_response=state.get("human_override_response"),network_released=state.get("network_released", False),network_release_status=state.get("network_release_status"),reasoning_trace=state.get("reasoning_trace", []),)
        entry = AuditLogEntry(incident_id=state["incident_id"],cluster_id=state["cluster_id"],severity_tier=state["severity_tier"],network_grant=state.get("network_grant"),network_denied=state.get("network_denied"),actuation_result=result,)
        sink(entry)
        logger.info("audit_entry_written incident_id=%s decision=%s entry_id=%s",state["incident_id"], result.decision, entry.entry_id,)
        return {**state, "audit_entry": entry}

    return audit_writer_node
"""Terminal node in the graph it assembles the full ActuationResult and
AuditLogEntry from accumulated state and persists it via an injected sink
(so tests can use an in-memory sink, and production can use a real
append-only log store / database table)."""