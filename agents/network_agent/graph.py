import json
import logging
from typing import Annotated, Sequence, TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from agents.network_agent.nodes.network_llm import NetworkAgent
from agents.network_agent.nodes.collect_requests import RequestCollector
from agents.network_agent.nodes.rank_requests import rank_requests
from agents.network_agent.nodes.group_requests import group_requests_by_zone
from agents.network_agent.nodes.dispatch_to_response import dispatch_node

logger = logging.getLogger("network_agent.graph")

VALID_DESERT_CLUSTERS = {
    "cluster-desert-042",
    "cluster-desert-043",
    "cluster-desert-044",
    "cluster-desert-045",
    "cluster-desert-046",
}


def sanitize_request(req: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures each request strictly identifies target device/cluster as a valid desert cluster."""
    target = (
        req.get("cluster_id")
        or req.get("sensor_cluster_id")
        or req.get("device_id")
    )
    if target not in VALID_DESERT_CLUSTERS:
        target = "cluster-desert-046"

    req["device_id"] = target
    req["cluster_id"] = target
    req["sensor_cluster_id"] = target
    return req


class NetworkWorkflowState(TypedDict):
    raw_requests: List[Dict[str, Any]]
    ranked_requests: List[Dict[str, Any]]
    regional_batches: List[Dict[str, Any]]
    messages: Annotated[Sequence[BaseMessage], add_messages]


def collect_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    collector = RequestCollector(max_batch_size=10, max_wait_time=2.0)
    for request in state.get("raw_requests", []):
        collector.add_request(sanitize_request(request))
        
    batch = collector.get_batch()
    return {"raw_requests": batch}


def rank_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    raw_reqs = [sanitize_request(r) for r in state.get("raw_requests", [])]
    ranked = rank_requests(raw_reqs)
    return {"ranked_requests": ranked}


def group_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    ranked_reqs = state.get("ranked_requests", [])
    grouped_batches = group_requests_by_zone(ranked_reqs)
    logger.info(
        "group_requests_complete requests=%d zones=%d",
        len(ranked_reqs),
        len(grouped_batches),
    )
    
    prompt_text = (
        "Process the following network resource requests grouped by regional zone:\n"
        f"{json.dumps(grouped_batches, indent=2)}\n\n"
        "STRICT TOOL CALLING RULES:\n"
        "- When invoking tools (like request_qod or request_slicing), the 'device_id' MUST be one of the following valid desert cluster IDs:\n"
        "  ['cluster-desert-042', 'cluster-desert-043', 'cluster-desert-044', 'cluster-desert-045', 'cluster-desert-046']\n"    )
    
    return {
        "regional_batches": grouped_batches,
        "messages": [HumanMessage(content=prompt_text)]
    }


network_agent_runner = NetworkAgent()


def agent_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    logger.info("network_policy_start messages=%d", len(state.get("messages", [])))
    agent_output = network_agent_runner.agent.invoke({"messages": state["messages"]})
    output_messages = agent_output.get("messages", [])
    response = output_messages[-1]
    response_metadata = getattr(response, "response_metadata", {}) or {}
    logger.info(
        "network_model_response type=%s tool_calls=%s finish_reason=%s",
        type(response).__name__,
        getattr(response, "tool_calls", None),
        response_metadata.get("finish_reason"),
    )
    logger.info(
        "network_message_trace %s",
        [
            {
                "index": index,
                "type": type(message).__name__,
                "name": getattr(message, "name", None),
                "tool_calls": [call.get("name") for call in (getattr(message, "tool_calls", None) or [])],
            }
            for index, message in enumerate(output_messages)
        ],
    )
    logger.info("network_policy_complete messages=%d", len(output_messages))
    return {"messages": output_messages}


workflow = StateGraph(NetworkWorkflowState)
workflow.add_node("collect_requests", collect_node)
workflow.add_node("rank_requests", rank_node)
workflow.add_node("group_requests", group_node)
workflow.add_node("network_agent", agent_node)
workflow.add_node("dispatch_to_response", dispatch_node)
workflow.add_edge(START, "collect_requests")
workflow.add_edge("collect_requests", "rank_requests")
workflow.add_edge("rank_requests", "group_requests")
workflow.add_edge("group_requests", "network_agent")
workflow.add_edge("network_agent", "dispatch_to_response")
workflow.add_edge("dispatch_to_response", END)
graph = workflow.compile()