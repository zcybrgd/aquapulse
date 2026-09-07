from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from agents.network_agent.nodes.tools.emit_output import emit_deny, emit_grant
from agents.network_agent.nodes.tools.request_qod import request_qod
from agents.network_agent.nodes.tools.request_slicing import request_network_slice
from agents.network_agent.nodes.tools.check_congestion import check_congestion
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, api_key=api_key)

tools = [check_congestion, request_qod, request_network_slice, emit_grant, emit_deny]

SYSTEM_PROMPT = """You are the Autonomous Network Quality Orchestrator for AquaPulse (MENA Water Pipeline Infrastructure).

GOAL: Dynamically manage cellular resources to guarantee critical telemetry and emergency valve actuations while minimizing network overhead and respecting regional cell capacity.

PRINCIPLES:
1. Allocation tiers:
   - Slicing: isolated, guaranteed throughput, high overhead. For multi-device coordination or very critical and severe threats.
   - QoD: lightweight, rapid, low overhead. For transient single-device priority or moderate telemetry spikes.
   - Best-Effort/No Allocation: for normal logging, non-critical alerts, or when congestion makes overrides wasteful.
2. Weigh asset criticality against regional cell congestion before escalating priority.
3. Never allocate to unreachable/offline devices — check reachability first.

REASONING:
- Assess physical urgency vs. asset criticality.
- Assess cell congestion and device reachability.
- Justify the chosen action (Slice, QoD, SMS fallback, or Deny) as the most resource-efficient.

EXECUTION:
- If the decision is Slice or QoD, call `request_network_slice` or `request_qod` first, then call `emit_grant` with the result — never fabricate session_id, expires_at, or granted_at; copy them exactly from the allocation tool's result.
- If the decision is Slice for more than one device, call `request_network_slice` once with all the requesting devices in a; single batch.
- If a tool call errors, retry it exactly once. If it fails again, call `emit_deny` with fallback "SMS" and a reason stating the tool call failed.
- If the decision is Deny/Best-Effort/No Allocation, do NOT call any allocation tool — call `emit_deny` directly with fallback "SMS" or "none" as appropriate.
- Process every request in the input batch this way, in order. Do not skip any request. Do not add commentary outside tool calls.
"""

class NetworkAgent:
    def __init__(self):
        self.agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )

    def run(self, input_text: str):
        return self.agent.invoke([HumanMessage(content=input_text)])
