from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class SeverityTier(IntEnum):
    TIER_1_MONITOR = 1  #log
    TIER_2_ALERT = 2 # alert human operator
    TIER_3_AUTONOMOUS = 3# autonomous valve isolation + simultaneous human alert

class NetworkGrant(BaseModel):
    #emitted by the Network Management Agent when a network resource request has been successfully allocated
    cluster_id: str
    incident_id: str
    severity_tier: SeverityTier
    guarantee_type: Literal["QoD", "slice"]
    session_id: str
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    reasoning_trace: str = ""

class NetworkDenied(BaseModel):
    #emitted by the second Agent when a network request could not be fulfilled (congestion, rate cap, API failure)
    cluster_id: str
    incident_id: str
    severity_tier: SeverityTier
    reason: str = ""  # accepted for backward compat
    reasoning_trace: str = ""
    fallback: Literal["SMS", "none"] = "SMS"
    denied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("reasoning_trace", mode="before")
    @classmethod
    def _mirror_reason(cls, v, info):
        # her schema calls it reasoning_trace; older internal callers used `reason`.
        # Keep both populated so nothing downstream breaks either way.
        return v or info.data.get("reason", "")

class ReachabilityStatus(BaseModel):
    #Result of a Device Reachability API call, made immediately before any command is sent not earlier since a device can go unreachable between detection and action
    device_id: str
    reachable: bool
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_signal_quality: Optional[str] = None

class ActuationDecision(str, Enum):
    LOG_ONLY = "log_only"
    ALERT_AND_AWAIT = "alert_and_await"
    AUTONOMOUS_ISOLATE = "autonomous_isolate"
    ESCALATE_UNREACHABLE = "escalate_unreachable"  # device unreachable so we can't act

class ActuationResult(BaseModel):
    #the final complete record of what this agent decided and did for one incident
    #This is what gets rendered on dashboard's live reasoning trace and written to the audit log.
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    cluster_id: str
    device_id: str
    severity_tier: SeverityTier
    reachability: ReachabilityStatus
    decision: ActuationDecision
    notification_sent: bool = False
    valve_command_sent: bool = False
    valve_command_confirmed: bool = False
    human_override_requested: bool = False
    human_override_response: Optional[Literal["confirmed", "overridden", "timed_out"]] = None
    network_released: bool = False
    network_release_status: Optional[str] = None
    reasoning_trace: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    @field_validator("severity_tier", mode="before")
    @classmethod
    def enforce_ceiling(cls, v):
        if isinstance(v, int):
            if v > SeverityTier.TIER_3_AUTONOMOUS:
                raise ValueError(f"Severity tier {v} exceeds the hard ceiling of "
                f"{SeverityTier.TIER_3_AUTONOMOUS}. Refusing to process.")
            return SeverityTier(v)
        return v

class AuditLogEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    cluster_id: str
    severity_tier: SeverityTier
    network_grant: Optional[NetworkGrant] = None
    network_denied: Optional[NetworkDenied] = None
    actuation_result: ActuationResult
    logged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))