"""
Dispatches finalized network decisions (QoD grants/denials, and any explicit
deny regardless of guarantee type) to the Response Agent immediately.

Slice grants are intentionally NOT dispatched here: request_network_slice
only returns status="INITIATED", not a confirmed allocation. The real
NetworkGrant for a slice is emitted later by webhook_server.py once the
slice lifecycle reaches OPERATING (or a terminal failure), because that's
the earliest point at which the guarantee is actually real.
"""
import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage, ToolMessage

from agents.network_agent.nodes.response_dispatch import dispatch_grant_or_deny

logger = logging.getLogger("network_agent.nodes.dispatch")

_DISPATCHABLE_TOOLS = {"emit_grant", "emit_deny"}


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
    skipped_slice_grants = 0

    for item in _extract_emitted_decisions(messages):
        decision = item["decision"]
        is_grant = item["tool"] == "emit_grant"
        device_id = item.get("device_id")
        if is_grant and decision.get("guarantee_type") == "slice":
            # Deferred: webhook_server will dispatch once the slice is OPERATING.
            skipped_slice_grants += 1
            continue

        try:
            dispatch_grant_or_deny(decision, is_grant=is_grant, device_id=device_id)
            dispatched += 1
        except Exception:
            logger.exception( "dispatch_to_response_FAILED incident_id=%s tool=%s",
                decision.get("incident_id"), item["tool"],)

    logger.info("dispatch_node_complete dispatched=%d deferred_slice_grants=%d", dispatched, skipped_slice_grants)
    return {}