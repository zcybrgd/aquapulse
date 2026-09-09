from __future__ import annotations

import logging
from typing import Optional
from langgraph.graph import END, StateGraph

from aia.clients.camara_client import CamaraClient
from aia.clients.topology import TopologyCache
from aia.models import ClusterInvestigationState
from aia.nodes.investigation import investigate
from aia.nodes.narration import narrate
from aia.nodes.risk import assess_risk

try:
    from agents.shared.llm_client import get_groq_llm
except ImportError:
    try:
        from shared.llm_client import get_groq_llm
    except ImportError:
        get_groq_llm = None

logger = logging.getLogger("aia.graph.builder")


def _investigate_node_factory(camara_client: CamaraClient):
    def _node(state: ClusterInvestigationState) -> ClusterInvestigationState:
        return investigate(state, camara_client)
    return _node


def _risk_node_factory(topology: TopologyCache):
    def _node(state: ClusterInvestigationState) -> ClusterInvestigationState:
        return assess_risk(state, topology)
    return _node


def _narration_node_factory(llm_client, model: str):
    def _node(state: ClusterInvestigationState) -> ClusterInvestigationState:
        state.operator_justification = narrate(state, llm_client, model)
        return state
    return _node


def build_investigation_graph(
    camara_client: CamaraClient,
    topology: TopologyCache,
    llm_client=None,
    model: str = "openai/gpt-oss-20b",
):
    """
    Builds the LangGraph investigation workflow.
    Ensures fallback to the centralized rate-limited LLM client if none is provided.
    """
    if llm_client is None and get_groq_llm is not None:
        try:
            llm_client = get_groq_llm(model=model)
            logger.debug("Auto-initialized shared rate-limited ChatGroq instance in builder graph.")
        except Exception as exc:
            logger.warning("Could not auto-initialize shared rate-limited LLM in build_investigation_graph: %s", exc)

    graph = StateGraph(ClusterInvestigationState)

    graph.add_node("investigate", _investigate_node_factory(camara_client))
    graph.add_node("assess_risk", _risk_node_factory(topology))
    graph.add_node("narrate", _narration_node_factory(llm_client, model))

    graph.set_entry_point("investigate")
    graph.add_edge("investigate", "assess_risk")
    graph.add_edge("assess_risk", "narrate")
    graph.add_edge("narrate", END)

    return graph.compile()