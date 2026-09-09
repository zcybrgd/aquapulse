from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.shared.llm_client import get_groq_llm
from ..schemas import ActuationDecision, SeverityTier
from ..state import ActuationState

logger = logging.getLogger("actuation_agent.nodes.llm_decision")

# Load prompt text safely with a fallback default
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompt.md"
try:
    SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
except Exception as exc:
    logger.warning("Could not read prompt.md at %s (%s) — using default system prompt", _PROMPT_PATH, exc)
    SYSTEM_PROMPT = (
        "You are the Autonomous Response Decision Planner for AquaPulse. "
        "Analyze anomaly severity, device reachability, and network state "
        "to recommend appropriate actuation actions and operator notifications."
    )


class LLMActuationDecision(BaseModel):
    decision: ActuationDecision
    operator_message: str = Field(..., description="Operator-facing notification text")
    reasoning: str = Field(..., description="Grounded justification for the decision")


_CACHED_CHAIN = None


def build_llm_decision_chain(force_rebuild: bool = False):
    """
    Builds or returns a cached decision chain configured with the rate-limited LLM factory.
    """
    global _CACHED_CHAIN
    if _CACHED_CHAIN is not None and not force_rebuild:
        return _CACHED_CHAIN

    llm = get_groq_llm()
    structured_llm = llm.with_structured_output(LLMActuationDecision)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        ("human", "incident_id: {incident_id}\n"
                  "device_id: {device_id}\n"
                  "severity_tier: {severity_tier}\n"
                  "device_reachable: {reachable}\n"
                  "signal_quality: {signal_quality}\n"
                  "network_guarantee_type: {guarantee_type}\n"
                  "network_denied_reason: {network_denied_reason}\n"
                  "network_fallback_channel: {network_fallback}\n"
                  "Propose the decision, draft the operator message, and explain your reasoning. "
                  "If the network guarantee was denied, mention in your reasoning that you are "
                  "acting without a guaranteed connection, and note this is elevated risk."),
    ])
    _CACHED_CHAIN = prompt | structured_llm
    return _CACHED_CHAIN


def _enforce_guardrails(proposed: ActuationDecision, tier: SeverityTier, reachable: bool) -> ActuationDecision:
    """Physical actuation logic must never depend on network state alone."""
    if not reachable:
        return ActuationDecision.ESCALATE_UNREACHABLE
    return {
        SeverityTier.TIER_1_MONITOR: ActuationDecision.LOG_ONLY,
        SeverityTier.TIER_2_ALERT: ActuationDecision.ALERT_AND_AWAIT,
        SeverityTier.TIER_3_AUTONOMOUS: ActuationDecision.AUTONOMOUS_ISOLATE,
    }[tier]


_FALLBACK_MESSAGES = {
    ActuationDecision.LOG_ONLY: "Tier 1 anomaly logged for monitoring. No action required.",
    ActuationDecision.ALERT_AND_AWAIT: "Tier 2 anomaly confirmed. Please review and confirm recommended action.",
    ActuationDecision.AUTONOMOUS_ISOLATE: "CRITICAL: Tier 3 event. Autonomous valve isolation triggered. Override window open.",
    ActuationDecision.ESCALATE_UNREACHABLE: "URGENT: Device unreachable. Manual intervention required — automated action withheld.",
}


def make_llm_decision_node(chain=None):
    """
    Factory function producing the LangGraph decision node.
    """
    def llm_decision_node(state: ActuationState) -> ActuationState:
        active_chain = chain or build_llm_decision_chain()
        reachability = state["reachability"]
        tier: SeverityTier = state["severity_tier"]
        incident_id = state["incident_id"]
        trace = list(state.get("reasoning_trace", []))
        grant = state.get("network_grant")
        denied = state.get("network_denied")

        if denied is not None:
            trace.append(f"Network priority reservation DENIED ({denied.reason}); proceeding without "
                         f"guaranteed bandwidth — fallback channel: {denied.fallback}.")
        elif grant is not None:
            trace.append(f"Network priority reservation ACTIVE (guarantee_type={grant.guarantee_type}, "
                         f"session_id={grant.session_id}).")
        else:
            trace.append("No network reservation was requested or recorded for this incident.")

        raw_sq = str(reachability.raw_signal_quality) if reachability.raw_signal_quality is not None else "-75 dBm"

        try:
            llm_out: LLMActuationDecision = active_chain.invoke({
                "incident_id": incident_id,
                "device_id": state["device_id"],
                "severity_tier": int(tier),
                "reachable": reachability.reachable,
                "signal_quality": raw_sq,
                "guarantee_type": grant.guarantee_type if grant else None,
                "network_denied_reason": denied.reason if denied else None,
                "network_fallback": denied.fallback if denied else None,
            })
            proposed, message, reasoning = llm_out.decision, llm_out.operator_message, llm_out.reasoning
        except Exception as exc:  # noqa: BLE001
            logger.error("llm_decision_FAILED incident_id=%s error=%s — falling back to rule-based decision", incident_id, exc)
            proposed = _enforce_guardrails(ActuationDecision.LOG_ONLY, tier, reachability.reachable)
            message = _FALLBACK_MESSAGES[proposed]
            reasoning = f"LLM call failed ({exc}); used deterministic fallback."

        decision = _enforce_guardrails(proposed, tier, reachability.reachable)
        if decision != proposed:
            trace.append(f"LLM proposed '{proposed}' but guardrail overrode to '{decision}' "
                         f"(tier={int(tier)}, reachable={reachability.reachable}).")
            message = _FALLBACK_MESSAGES[decision]

        trace.append(f"LLM reasoning: {reasoning}")
        return {
            **state,
            "decision": decision,
            "operator_message": message,
            "human_override_requested": decision == ActuationDecision.AUTONOMOUS_ISOLATE,
            "reasoning_trace": trace,
        }

    return llm_decision_node