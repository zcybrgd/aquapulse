from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agents.response_agent.graph import build_actuation_graph
from agents.response_agent.schemas import (
    NetworkDenied as RANetworkDenied,
    NetworkGrant as RANetworkGrant,
    SeverityTier as RASeverityTier,
)

logger = logging.getLogger("network_agent.nodes.response_dispatch")

# Non-blocking ThreadPoolExecutor for fire-and-forget execution of response graphs
_DISPATCH_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="response-dispatch")

_response_graph = None


def _get_response_graph():
    """Lazy loader for Response Agent graph to prevent circular import delays."""
    global _response_graph
    if _response_graph is None:
        _response_graph = build_actuation_graph()
    return _response_graph


def _parse_datetime(dt_val: Any) -> Optional[datetime]:
    """Safely converts ISO datetime strings or datetime objects to timezone-aware UTC objects."""
    if dt_val is None:
        return None
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    if isinstance(dt_val, str):
        try:
            dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("Failed to parse datetime string: %s", dt_val)
            return None
    return None


def _to_ra_grant(decision: Dict[str, Any]) -> RANetworkGrant:
    granted_at = _parse_datetime(decision.get("granted_at")) or datetime.now(timezone.utc)
    expires_at = _parse_datetime(decision.get("expires_at"))

    return RANetworkGrant(
        cluster_id=decision["cluster_id"],
        incident_id=decision["incident_id"],
        severity_tier=RASeverityTier(int(decision["severity_tier"])),
        guarantee_type=decision["guarantee_type"],
        session_id=decision["session_id"],
        granted_at=granted_at,
        expires_at=expires_at,
        reasoning_trace=decision.get("reasoning_trace", ""),
    )


def _to_ra_denied(decision: Dict[str, Any]) -> RANetworkDenied:
    return RANetworkDenied(
        cluster_id=decision["cluster_id"],
        incident_id=decision["incident_id"],
        severity_tier=RASeverityTier(int(decision["severity_tier"])),
        reason=decision.get("reasoning_trace", "denied"),
        fallback=decision.get("fallback", "SMS"),
    )


def _invoke_response_graph(
    *,
    incident_id: str,
    cluster_id: str,
    device_id: str,
    severity_tier: int,
    grant: Optional[RANetworkGrant],
    denied: Optional[RANetworkDenied],
    operator_contact: str,
) -> None:
    app = _get_response_graph()
    initial_state = {
        "incident_id": incident_id,
        "cluster_id": cluster_id,
        "device_id": device_id,
        "severity_tier": RASeverityTier(int(severity_tier)),
        "network_grant": grant,
        "network_denied": denied,
        "operator_contact": operator_contact,
        "reasoning_trace": [],
    }
    try:
        final_state = app.invoke(initial_state)
        logger.info(
            "response_agent_invoked incident_id=%s decision=%s",
            incident_id, final_state.get("decision"),
        )
    except Exception as exc:
        logger.exception(
            "response_agent_invoke_FAILED incident_id=%s device_id=%s error=%s",
            incident_id, device_id, exc
        )


def dispatch_grant_or_deny(
    decision: Dict[str, Any],
    *,
    is_grant: bool,
    device_id: Optional[str] = None,
    operator_contact: str = "",
) -> None:
    """
    Fire-and-forget dispatch to the Response Agent's graph.
    `decision` is the raw dict produced by emit_grant/emit_deny (or the
    equivalent built by the slice-webhook lifecycle).
    """
    try:
        incident_id = decision.get("incident_id") or str(uuid.uuid4())
        cluster_id = decision["cluster_id"]
        severity_tier = int(decision["severity_tier"])
        resolved_device_id = device_id or decision.get("device_id") or "unknown-device"

        grant = _to_ra_grant(decision) if is_grant else None
        denied = None if is_grant else _to_ra_denied(decision)

        _DISPATCH_POOL.submit(
            _invoke_response_graph,
            incident_id=incident_id,
            cluster_id=cluster_id,
            device_id=resolved_device_id,
            severity_tier=severity_tier,
            grant=grant,
            denied=denied,
            operator_contact=operator_contact,
        )
        logger.debug(
            "Dispatched background actuation worker for incident_id=%s (grant=%s)",
            incident_id, is_grant,
        )
    except Exception as exc:
        logger.exception("Failed to prepare or submit response dispatch job: %s", exc)