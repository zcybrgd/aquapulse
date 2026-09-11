"""
Dispatches finalized network decisions (grants and denials) to the Response Agent.
"""
import json
import logging
import uuid
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage, ToolMessage

from agents.network_agent.nodes.response_dispatch import dispatch_grant_or_deny

logger = logging.getLogger("network_agent.nodes.dispatch")

_DISPATCHABLE_TOOLS = {"emit_grant", "emit_deny"}


def _fallback_denial(request: Dict[str, Any]) -> Dict[str, Any]:
    cluster_id = request.get("cluster_id") or request.get("sensor_cluster_id") or request.get("device_id")
    return {
        "cluster_id": cluster_id,
        "incident_id": request.get("anomaly_id") or request.get("incident_id") or str(uuid.uuid4()),
        "device_id": request.get("device_id") or cluster_id,
        "severity_tier": request.get("severity_tier", 1),
        "reasoning_trace": "Network policy did not emit a final allocation decision; using SMS fallback.",
        "fallback": "SMS",
    }


def _extract_emitted_decisions(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    decisions = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name not in _DISPATCHABLE_TOOLS:
            continue
        try:
            payload = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (TypeError, json.JSONDecodeError):
            logger.warning("dispatch_skip_unparsable_tool_message tool=%s", msg.name)
            continue
        decision = payload.get("decision")
        if not decision:
            continue
        decisions.append({
            "tool": msg.name,
            "status": payload.get("status"),
            "decision": decision,
            "device_id": payload.get("device_id"),
        })
    return decisions


def dispatch_node(state: Dict[str, Any]) -> Dict[str, Any]:
    messages = state.get("messages", [])
    dispatched = 0
    decisions = _extract_emitted_decisions(messages)
    decided_incidents = {
        item["decision"].get("incident_id")
        for item in decisions
    }

    for request in state.get("raw_requests", []):
        incident_id = request.get("anomaly_id") or request.get("incident_id")
        if incident_id and incident_id not in decided_incidents:
            logger.warning(
                "network_policy_missing_final_decision incident_id=%s severity_tier=%s; applying denial fallback",
                incident_id,
                request.get("severity_tier", 1),
            )
            decisions.append({
                "tool": "emit_deny",
                "decision": _fallback_denial(request),
                "device_id": request.get("device_id"),
            })

    for item in decisions:
        decision = item["decision"]
        is_grant = item["tool"] == "emit_grant"
        device_id = item.get("device_id")

        try:
            dispatch_grant_or_deny(decision, is_grant=is_grant, device_id=device_id)
            dispatched += 1
        except Exception:
            logger.exception(
                "dispatch_to_response_FAILED incident_id=%s tool=%s",
                decision.get("incident_id"),
                item["tool"],
            )

    logger.info("dispatch_node_complete dispatched=%d", dispatched)
    return {}