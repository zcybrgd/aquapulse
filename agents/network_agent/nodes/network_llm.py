from __future__ import annotations

import logging
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from agents.shared.llm_client import get_groq_llm
from agents.network_agent.nodes.tools.emit_output import emit_deny, emit_grant
from agents.network_agent.nodes.tools.request_qod import request_qod
from agents.network_agent.nodes.tools.request_slicing import request_network_slice
from agents.network_agent.nodes.tools.check_congestion import check_congestion

load_dotenv()

logger = logging.getLogger(__name__)

TOOLS = [check_congestion, request_qod, request_network_slice, emit_grant, emit_deny]

SYSTEM_PROMPT = """You are the Autonomous Network Quality Orchestrator for AquaPulse (MENA Water Pipeline Infrastructure).

GOAL: Dynamically manage cellular resources to guarantee critical telemetry and emergency valve actuations while minimizing network overhead and respecting regional cell capacity.

PRINCIPLES:
1. Allocation Tiers:
   - Slicing: Isolated, guaranteed SLA. Use for multi-device fleets, sustained operational windows, or top-tier critical threats requiring hard network isolation.
   - QoD (Quality on Demand): Dynamic, rapid setup (seconds), duration-bound/transient. Use for single-device priority boosts, short-lived telemetry spikes, or moderate transient threats.
   - Best-Effort / No Allocation: Default network transport. Use for routine logging, low-severity alerts, or when severe congestion makes allocation wasteful.
2. Weigh asset criticality against regional cell congestion before escalating priority.
3. Never allocate to unreachable/offline devices — check reachability first.

REASONING:
- Assess physical urgency vs. asset criticality.
- Assess cell congestion and device reachability.
- Justify the chosen action (Slice, QoD, SMS fallback, or Deny) as the most resource-efficient.

EXECUTION:
- If the decision is Slice or QoD, call `request_network_slice` or `request_qod` first, then call `emit_grant` with the result — never fabricate session_id, expires_at, or granted_at; copy them exactly from the allocation tool's result. Always pass `device_id` copied verbatim from the input request being processed — never invent it, never leave it blank.
- Note that calling `request_network_slice` automatically attaches/binds the specified target device(s) to it.
- If the decision is Slice for more than one device, call `request_network_slice` once with all the requesting devices in a single batch to attach them together under the same slice.
- For QoD: only call `emit_grant` if `request_qod`'s returned status is exactly "AVAILABLE". If the status is "REQUESTED" (still pending after polling), "UNAVAILABLE", or "FAILED", call `emit_deny` with fallback "SMS" instead — do not treat a pending/unconfirmed QoD session as a grant.
- If a tool call errors, retry it exactly once. If it fails again, call `emit_deny` with fallback "SMS" and a reason stating the tool call failed.
- If the decision is Deny/Best-Effort/No Allocation, do NOT call any allocation tool — call `emit_deny` directly with fallback "SMS" or "none" as appropriate.
- Process every request in the input batch this way, in order. Do not skip any request. Do not add commentary outside tool calls.
"""

class NetworkAgent:
    def __init__(self, llm=None):
        """
        Initializes the NetworkAgent using the central rate-limited LLM factory.
        Allows injecting a custom LLM instance for testing.
        """
        self.llm = llm or get_groq_llm()
        self.agent = create_agent(
            model=self.llm,
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, input_text: str):
        logger.info("Executing NetworkAgent orchestration step")
        return self.agent.invoke([HumanMessage(content=input_text)])