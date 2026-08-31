"""
LangGraph orchestrator (Section 6).

Wires the per-cluster investigation as a small state graph:

    investigate --> [requeue?] --> END (requeued for next batch cycle)
                 --> assess_risk --> narrate --> END

Stage 1 (detection) runs outside the graph, over the full batch, before any
suspicious cluster ever reaches the graph -- this matches the spec's
explicit separation between the "extremely low cost" detection stage and the
"agentic" investigation stage (Section 4).

The graph operates on one `ClusterInvestigationState` per suspicious cluster.
Batch-level fan-out/fan-in (running the graph once per suspicious cluster,
collecting results, and compiling the final payload) is handled in
`pipeline.py`.
"""
from __future__ import annotations

from typing import Optional

from langgraph.graph import END, StateGraph

from aia.camara_client import CamaraClient
from aia.investigation import investigate
from aia.models import ClusterInvestigationState
from aia.narration import narrate
from aia.risk import assess_risk
from aia.topology import TopologyCache


def _investigate_node_factory(camara_client: CamaraClient):
    def _node(state: ClusterInvestigationState) -> ClusterInvestigationState:
        return investigate(state, camara_client)
    return _node


def _risk_node_factory(topology: TopologyCache):
    def _node(state: ClusterInvestigationState) -> ClusterInvestigationState:
        return assess_risk(state, topology)
    return _node


def _narration_node_factory(anthropic_client, model: str):
    def _node(state: ClusterInvestigationState) -> ClusterInvestigationState:
        state.operator_justification = narrate(state, anthropic_client, model)
        return state
    return _node


def build_investigation_graph(
    camara_client: CamaraClient,
    topology: TopologyCache,
    anthropic_client=None,
    model: str = "claude-sonnet-4-6",
):
    """
    Builds and compiles the per-cluster LangGraph investigation graph.
    `anthropic_client` may be None, in which case Stage 4 falls back to the
    deterministic template narrator (see narration.py).

    Note: `insufficient_data` clusters still flow through assess_risk (which
    applies the fallback tier from Section 8's Actionable Interpretation
    Matrix) and narrate, since the NMA must receive an immediate
    "insufficient_data" payload AND the cluster gets re-queued for the next
    batch cycle (Section 5.B.4) -- these are not mutually exclusive. The
    `requeue`/`escalate_to_human` flags on the returned state tell the
    batch-level pipeline (pipeline.py) how to handle the next cycle.
    """
    graph = StateGraph(ClusterInvestigationState)

    graph.add_node("investigate", _investigate_node_factory(camara_client))
    graph.add_node("assess_risk", _risk_node_factory(topology))
    graph.add_node("narrate", _narration_node_factory(anthropic_client, model))

    graph.set_entry_point("investigate")
    graph.add_edge("investigate", "assess_risk")
    graph.add_edge("assess_risk", "narrate")
    graph.add_edge("narrate", END)

    return graph.compile()
