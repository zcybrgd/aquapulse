from __future__ import annotations
from typing import Any, Dict, Optional

from ..schemas import ActuationDecision, AuditLogEntry

_DECISION_MAP = {
    ActuationDecision.LOG_ONLY: "LOG_ONLY",
    ActuationDecision.ALERT_AND_AWAIT: "ALERT_AND_AWAIT",
    ActuationDecision.AUTONOMOUS_ISOLATE: "AUTONOMOUS_ISOLATE",
    ActuationDecision.ESCALATE_UNREACHABLE: "ESCALATE_UNREACHABLE",
}


def _summarize_actuation(entry: AuditLogEntry) -> str:
    """
    audit.actuation_result on AquaPulse's side is a plain string, not an
    object. Summarize the meaningful outcome in one short phrase rather
    than dumping JSON into a text field.
    """
    result = entry.actuation_result
    if result.decision == ActuationDecision.AUTONOMOUS_ISOLATE:
        if result.valve_command_confirmed:
            return "valve_isolated_confirmed"
        if result.valve_command_sent:
            return "valve_isolation_attempted_unconfirmed"
        return "not_executed"
    if result.decision == ActuationDecision.LOG_ONLY:
        return "not_executed"
    return "not_executed"


def _network_grant_block(entry: AuditLogEntry) -> Optional[Dict[str, Any]]:
    grant = entry.network_grant
    if grant is None:
        return None
    return {
        "granted": True,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "grant_id": grant.session_id,
        "data_mode": "simulated",
    }


def _network_denied_block(entry: AuditLogEntry) -> Optional[Dict[str, Any]]:
    denied = entry.network_denied
    if denied is None:
        return None
    reason = denied.reasoning_trace or denied.reason or None
    return {
        "denied": True,
        "reason": reason,
        "data_mode": "simulated",
    }


def to_response_result_v1(entry: AuditLogEntry) -> Dict[str, Any]:
    """
    Builds a dict matching ResponseResultV1 exactly, ready for
    POST to the validate-response route (and, once implemented,
    the real ingest route).
    """
    result = entry.actuation_result

    payload: Dict[str, Any] = {
        "schema_version": "1.0",
        "result_id": result.result_id,
        "incident_id": entry.incident_id,
        "cluster_id": entry.cluster_id,
        "device_id": result.device_id,
        "severity_tier": int(entry.severity_tier),
        "reachability": {
            "device_id": result.reachability.device_id,
            "reachable": result.reachability.reachable,
            "checked_at": result.reachability.checked_at.isoformat(),
            "raw_signal_quality": result.reachability.raw_signal_quality,
        },
        "decision": _DECISION_MAP[result.decision],
        "notification_sent": result.notification_sent,
        "valve_command_sent": result.valve_command_sent,
        "valve_command_confirmed": result.valve_command_confirmed,
        "human_override_requested": result.human_override_requested,
        "human_override_response": result.human_override_response,
        "reasoning_trace": result.reasoning_trace,
        "created_at": result.created_at.isoformat(),
        "audit": {
            "entry_id": entry.entry_id,
            "incident_id": entry.incident_id,
            "cluster_id": entry.cluster_id,
            "severity_tier": int(entry.severity_tier),
            "network_grant": _network_grant_block(entry),
            "network_denied": _network_denied_block(entry),
            "actuation_result": _summarize_actuation(entry),
            "logged_at": entry.logged_at.isoformat(),
        },
    }
    return payload