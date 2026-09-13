from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agents.response_agent.graph import build_actuation_graph
from agents.response_agent.nodes.llm_response_planner import build_llm_decision_chain
from agents.response_agent.schemas import (
    NetworkDenied as RANetworkDenied,
    NetworkGrant as RANetworkGrant,
    SeverityTier as RASeverityTier,
)

logger = logging.getLogger("network_agent.nodes.response_dispatch")

_DISPATCH_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="response-dispatch")

_response_graph = None


def _get_response_graph():
    """Lazy loader for Response Agent graph configured for non-blocking execution."""
    global _response_graph
    if _response_graph is None:
        try:
            llm_chain = build_llm_decision_chain()
        except Exception as e:
            logger.warning("[ResponseAgent] Could not initialize LLM chain (%s). Proceeding with default graph.", e)
            llm_chain = None

        _response_graph = build_actuation_graph(
            llm_chain=llm_chain,
            override_window_seconds=0.0,  # Bypass 120s manual override delay
            override_poller=lambda incident_id: "confirmed",
        )
    return _response_graph


def _parse_datetime(dt_val: Any) -> Optional[datetime]:
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
        cluster_id=decision.get("cluster_id") or decision.get("sensor_cluster_id", "cluster-desert-046"),
        incident_id=decision.get("incident_id") or str(uuid.uuid4()),
        severity_tier=RASeverityTier(int(decision.get("severity_tier", 1))),
        guarantee_type=decision.get("guarantee_type") or decision.get("qos_profile", "QoD"),
        session_id=str(decision.get("session_id") or decision.get("qos_session_id") or uuid.uuid4()),
        granted_at=granted_at,
        expires_at=expires_at,
        reasoning_trace=str(decision.get("reasoning_trace", "")),
    )


def _to_ra_denied(decision: Dict[str, Any]) -> RANetworkDenied:
    return RANetworkDenied(
        cluster_id=decision.get("cluster_id") or decision.get("sensor_cluster_id", "cluster-desert-046"),
        incident_id=decision.get("incident_id") or str(uuid.uuid4()),
        severity_tier=RASeverityTier(int(decision.get("severity_tier", 1))),
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
    logger.info(
        "[ResponseAgent] Starting execution for incident_id=%s cluster=%s device=%s tier=%s",
        incident_id, cluster_id, device_id, severity_tier
    )
    try:
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
        final_state = app.invoke(initial_state)
        logger.info(
            "[ResponseAgent] SUCCESS incident_id=%s decision=%s",
            incident_id, final_state.get("decision"),
        )
        print(f"\n>>> [ResponseAgent] Actuation Completed Successfully for Incident {incident_id} <<<\n", flush=True)
    except Exception as exc:
        logger.exception(
            "[ResponseAgent] FAILED for incident_id=%s device_id=%s error=%s",
            incident_id, device_id, exc
        )


def _check_future_exception(future):
    """Logs any uncaught error swallowed by ThreadPoolExecutor."""
    try:
        future.result()
    except Exception as exc:
        logger.exception("[ResponseAgent] Background worker thread crashed with uncaught error: %s", exc)


def dispatch_grant_or_deny(
    decision: Dict[str, Any],
    *,
    is_grant: bool,
    device_id: Optional[str] = None,
    operator_contact: str = "",
) -> None:
    try:
        incident_id = decision.get("incident_id") or str(uuid.uuid4())
        cluster_id = decision.get("cluster_id") or decision.get("sensor_cluster_id", "cluster-desert-046")
        severity_tier = int(decision.get("severity_tier", 1))
        resolved_device_id = device_id or decision.get("device_id") or "unknown-device"

        grant = _to_ra_grant(decision) if is_grant else None
        denied = None if is_grant else _to_ra_denied(decision)

        future = _DISPATCH_POOL.submit(
            _invoke_response_graph,
            incident_id=incident_id,
            cluster_id=cluster_id,
            device_id=resolved_device_id,
            severity_tier=severity_tier,
            grant=grant,
            denied=denied,
            operator_contact=operator_contact,
        )
        future.add_done_callback(_check_future_exception)

        logger.info(
            "[ResponseAgent] Dispatched actuation task for incident_id=%s (grant=%s)",
            incident_id, is_grant,
        )
    except Exception as exc:
        logger.exception("Failed to prepare or submit response dispatch job: %s", exc)