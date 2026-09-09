import json
from typing import Annotated, Sequence, TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from agents.network_agent.nodes.network_llm import NetworkAgent
from agents.network_agent.nodes.collect_requests import RequestCollector
from agents.network_agent.nodes.rank_requests import rank_requests
from agents.network_agent.nodes.group_requests import group_requests_by_zone
from agents.network_agent.nodes.dispatch_to_response import dispatch_node

class NetworkWorkflowState(TypedDict):
    raw_requests: List[Dict[str, Any]]
    ranked_requests: List[Dict[str, Any]]
    regional_batches: List[Dict[str, Any]]
    messages: Annotated[Sequence[BaseMessage], add_messages]

def collect_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    collector = RequestCollector(max_batch_size=10, max_wait_time=2.0)
    for request in state.get("raw_requests", []):
        collector.add_request(request)
        
    batch = collector.get_batch()
    return {"raw_requests": batch}


def rank_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    raw_reqs = state.get("raw_requests", [])
    ranked = rank_requests(raw_reqs)
    return {"ranked_requests": ranked}


def group_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    ranked_reqs = state.get("ranked_requests", [])
    grouped_batches = group_requests_by_zone(ranked_reqs)
    
    prompt_text = (
        "Process the following network resource requests grouped by regional zone:\n"
        f"{json.dumps(grouped_batches, indent=2)}"
    )
    
    return {
        "regional_batches": grouped_batches,
        "messages": [HumanMessage(content=prompt_text)]
    }

network_agent_runner = NetworkAgent()

def agent_node(state: NetworkWorkflowState) -> Dict[str, Any]:
    agent_output = network_agent_runner.agent.invoke({"messages": state["messages"]})
    return {"messages": agent_output["messages"]}


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