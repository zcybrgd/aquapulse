from __future__ import annotations
import logging
from typing import Callable, Optional
from langgraph.graph import END, StateGraph
from .nodes.audit_writer import make_audit_writer_node
from .nodes.execute_response import make_execute_response_node
from .nodes.human_override import make_human_override_node
from .nodes.reachability_check import make_reachability_check_node
from .schemas import AuditLogEntry
from .state import ActuationState
from .tools.actuator_client import ValveActuatorClient
from .tools.notification_client import NotificationClient
from .tools.reachability_client import DeviceReachabilityClient
logger = logging.getLogger("actuation_agent.graph")


def jsonl_audit_sink(path: str = "audit_log.jsonl") -> Callable[[AuditLogEntry], None]:
    def sink(entry: AuditLogEntry) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
    return sink


def noop_override_poller(incident_id: str) -> Optional[str]:
    return None


def build_actuation_graph(reachability_client: Optional[DeviceReachabilityClient] = None,notification_client: Optional[NotificationClient] = None,actuator_client: Optional[ValveActuatorClient] = None,audit_sink: Optional[Callable[[AuditLogEntry], None]] = None,override_poller: Optional[Callable[[str], Optional[str]]] = None,override_window_seconds: float = 120.0,poll_interval_seconds: float = 2.0,):
    reachability_client = reachability_client or DeviceReachabilityClient()
    notification_client = notification_client or NotificationClient()
    actuator_client = actuator_client or ValveActuatorClient()
    audit_sink = audit_sink or jsonl_audit_sink()
    override_poller = override_poller or noop_override_poller
    graph = StateGraph(ActuationState)
    graph.add_node("reachability_check", make_reachability_check_node(reachability_client))
    graph.add_node("execute_response", make_execute_response_node(notification_client, actuator_client),)
    graph.add_node("human_override", make_human_override_node(override_poller, window_seconds=override_window_seconds, poll_interval_seconds=poll_interval_seconds),)
    graph.add_node("audit_writer", make_audit_writer_node(audit_sink))
    graph.set_entry_point("reachability_check")
    graph.add_edge("reachability_check", "execute_response")
    graph.add_edge("execute_response", "human_override")
    graph.add_edge("human_override", "audit_writer")
    graph.add_edge("audit_writer", END)
    return graph.compile()
default_graph = build_actuation_graph()
