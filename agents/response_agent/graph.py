from __future__ import annotations
import logging
from typing import Callable, Optional
from langgraph.graph import END, StateGraph
from .nodes.audit_writer import make_audit_writer_node
from .nodes.execute_response import make_execute_response_node
from .nodes.human_override import make_human_override_node
from .nodes.llm_response_planner import make_llm_decision_node
from .nodes.reachability_check import make_reachability_check_node
from .schemas import AuditLogEntry
from .state import ActuationState
from .tools.actuator_client import ValveActuatorClient
from .tools.notification_client import NotificationClient
from .tools.reachability_client import DeviceReachabilityClient
from .nodes.release_network import make_release_network_node
from .tools.network_release_agent import NetworkReleaseClient
from .nodes.publish_to_platform import make_publish_to_platform_node
from .tools.aquapulse_client import AquaPulsePlatformClient
logger = logging.getLogger("actuation_agent.graph")

def jsonl_audit_sink(path: str = "audit_log.jsonl") -> Callable[[AuditLogEntry], None]:
    def sink(entry: AuditLogEntry) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")
    return sink

def noop_override_poller(incident_id: str) -> Optional[str]:
    return None
def build_actuation_graph(
    reachability_client: Optional[DeviceReachabilityClient] = None,
    notification_client: Optional[NotificationClient] = None,
    actuator_client: Optional[ValveActuatorClient] = None,
    audit_sink: Optional[Callable[[AuditLogEntry], None]] = None,
    override_poller: Optional[Callable[[str], Optional[str]]] = None,
    llm_chain=None,
    override_window_seconds: float = 120.0,
    poll_interval_seconds: float = 2.0,
    network_release_client: Optional[NetworkReleaseClient] = None,
    aquapulse_client: Optional[AquaPulsePlatformClient] = None,
):
    reachability_client = reachability_client or DeviceReachabilityClient()
    notification_client = notification_client or NotificationClient()
    actuator_client = actuator_client or ValveActuatorClient()
    network_release_client = network_release_client or NetworkReleaseClient()
    aquapulse_client = aquapulse_client or AquaPulsePlatformClient()
    audit_sink = audit_sink or jsonl_audit_sink()
    override_poller = override_poller or noop_override_poller
    graph = StateGraph(ActuationState)
    graph.add_node("reachability_check", make_reachability_check_node(reachability_client))
    graph.add_node("llm_response_planner", make_llm_decision_node(llm_chain))
    graph.add_node("execute_response", make_execute_response_node(notification_client, actuator_client))
    graph.add_node("human_override", make_human_override_node(override_poller, window_seconds=override_window_seconds, poll_interval_seconds=poll_interval_seconds,))
    graph.add_node("release_network", make_release_network_node(network_release_client))
    graph.add_node("audit_writer", make_audit_writer_node(audit_sink))
    graph.add_node("publish_to_platform", make_publish_to_platform_node(aquapulse_client))
    graph.set_entry_point("reachability_check")
    graph.add_edge("reachability_check", "llm_response_planner")
    graph.add_edge("llm_response_planner", "execute_response")
    graph.add_edge("execute_response", "human_override")
    graph.add_edge("human_override", "release_network")
    graph.add_edge("release_network", "audit_writer")
    graph.add_edge("audit_writer", "publish_to_platform")
    graph.add_edge("publish_to_platform", END)
    return graph.compile()