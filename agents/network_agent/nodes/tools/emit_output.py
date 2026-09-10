from datetime import datetime, timezone
import json
from typing import Any, Dict, Literal, Optional, Union
from langchain_core.tools import tool
from agents.network_agent.schemas import NetworkDenied, NetworkGrant


@tool
def emit_grant(
    cluster_id: str,
    incident_id: str,
    device_id: str,
    severity_tier: Union[int, str],
    guarantee_type: Literal["QoD", "slice"],
    session_id: str,
    granted_at: str,
    reasoning_trace: str,
    expires_at: Optional[str] = None,
) -> str:
    """Emit the final decision for a request that was successfully allocated a network guarantee (Slice or QoD). 
    we call this once, after the allocation tool call has returned a result.
    Args:
        cluster_id: Copied verbatim from the input request.
        incident_id: Copied verbatim from the input request.
        device_id: Copied verbatim from the input request (the phone number used for the allocation). Never invent.
        severity_tier: Severity tier (numeric 1-3 or string). Copied verbatim from the input request.
        guarantee_type: Network guarantee allocated. Allowed values: 'QoD' or 'slice'.
        session_id: Copied from the allocation tool's result. Never invent.
        granted_at: ISO 8601 UTC timestamp, copied from the allocation tool's result. Never invent.
        reasoning_trace: Exactly one sentence justifying the decision (severity vs. congestion, reachability, etc.).
        expires_at: ISO 8601 UTC timestamp, copied from the allocation tool's result. Never invent.
    """
    decision = NetworkGrant(
        cluster_id=cluster_id,
        incident_id=incident_id,
        severity_tier=severity_tier,
        guarantee_type=guarantee_type,
        session_id=session_id,
        granted_at=granted_at,
        reasoning_trace=reasoning_trace,
        expires_at=expires_at,
    )
    return json.dumps(
        {"status": "GRANTED", "device_id": device_id, "decision": decision.model_dump(mode="json")}
    )


@tool
def emit_deny(
    cluster_id: str,
    incident_id: str,
    device_id: str,
    severity_tier: Union[int, str],
    fallback: Literal["SMS", "none"],
    reasoning_trace: str,
) -> str:
    """Emit the final decision for a request that was denied, either a deliberate Deny/Best-Effort classification, 
    or a failed allocation attempt after retry. Call this once per denied request.

    Args:
        cluster_id: Copied verbatim from the input request.
        incident_id: Copied verbatim from the input request.
        device_id: Copied verbatim from the input request.
        severity_tier: Severity tier (numeric 1-3 or string). Copied verbatim from the input request.
        fallback: Fallback strategy when denied. Allowed values: 'SMS' or 'none'.
        reasoning_trace: Exactly one sentence. If denial is due to tool failure, state that explicitly rather than citing congestion/severity.
    """
    decision = NetworkDenied(
        cluster_id=cluster_id,
        incident_id=incident_id,
        severity_tier=severity_tier,
        reasoning_trace=reasoning_trace,
        fallback=fallback,
        denied_at=datetime.now(timezone.utc),
    )
    return json.dumps(
        {"status": "DENIED", "device_id": device_id, "decision": decision.model_dump(mode="json")}
    )