from __future__ import annotations
from typing import Optional, TypedDict
from .schemas import (ActuationDecision,AuditLogEntry,NetworkDenied,NetworkGrant,ReachabilityStatus,SeverityTier,)
#shared state object threaded through the agent's langgraph graph
class ActuationState(TypedDict, total=False):
    #inputs
    incident_id: str
    cluster_id: str
    device_id: str
    severity_tier: SeverityTier
    network_grant: Optional[NetworkGrant]
    network_denied: Optional[NetworkDenied]
    operator_contact: str  # phone number / email for notifications
    # intermediate
    reachability: ReachabilityStatus
    decision: ActuationDecision
    notification_sent: bool
    valve_command_sent: bool
    valve_command_confirmed: bool
    human_override_requested: bool
    human_override_response: Optional[str]
    reasoning_trace: list[str]
    network_released: bool
    network_release_status: Optional[str]
    #outputs
    audit_entry: AuditLogEntry
    error: Optional[str]
    operator_message: str


