from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.integrations.constants import CONTRACT_VERSION, DECISIONS

SAFETY_FIELDS = {
    "decision",
    "severity_tier",
    "valve_command_sent",
    "valve_command_confirmed",
    "incident_id",
    "human_override_response",
    "notification_sent",
}


class NetworkGrantV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    granted: bool = False
    expires_at: datetime | None = None
    grant_id: str | None = None
    data_mode: str = "mock"


class NetworkDeniedV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    denied: bool = True
    reason: str | None = None
    data_mode: str = "mock"


class OperatorContactV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = "Demo Operator"
    channel: str = "unconfigured"


class ResponseRequestV1(BaseModel):
    schema_version: Literal["1.0"] = CONTRACT_VERSION
    run_id: str
    requested_at: datetime
    data_mode: str = "simulated"
    incident_id: str
    cluster_id: str
    device_id: str
    severity_tier: int
    network_grant: NetworkGrantV1
    network_denied: NetworkDeniedV1
    operator_contact: OperatorContactV1

    @field_validator("severity_tier")
    @classmethod
    def severity_range(cls, value: int) -> int:
        if value not in (1, 2, 3):
            raise ValueError("severity_tier must be 1, 2 or 3")
        return value

    @model_validator(mode="after")
    def grant_expiration(self) -> ResponseRequestV1:
        if self.network_grant.granted and self.network_grant.expires_at is None:
            raise ValueError("network_grant.expires_at is required when granted is true")
        return self


class ResponseAuditEntryV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    entry_id: str
    incident_id: str
    cluster_id: str
    severity_tier: int
    network_grant: dict[str, Any] | None = None
    network_denied: dict[str, Any] | None = None
    actuation_result: str | None = None
    logged_at: datetime


class ResponseResultV1(BaseModel):
    """Recommendation only. AquaPulse never treats this as authorization to actuate."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["1.0"] = CONTRACT_VERSION
    result_id: str
    incident_id: str
    cluster_id: str
    device_id: str
    severity_tier: int
    reachability: dict[str, Any] = Field(default_factory=dict)
    decision: Literal["LOG_ONLY", "ALERT_AND_AWAIT", "AUTONOMOUS_ISOLATE", "ESCALATE_UNREACHABLE"]
    notification_sent: bool = False
    valve_command_sent: bool = False
    valve_command_confirmed: bool = False
    human_override_requested: bool = False
    human_override_response: str | None = None
    reasoning_trace: list[Any] | dict[str, Any] = Field(default_factory=list)
    created_at: datetime
    audit: ResponseAuditEntryV1 | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity_tier")
    @classmethod
    def severity_range(cls, value: int) -> int:
        if value not in (1, 2, 3):
            raise ValueError("severity_tier must be 1, 2 or 3")
        return value

    @field_validator("decision")
    @classmethod
    def decision_allowed(cls, value: str) -> str:
        if value not in DECISIONS:
            raise ValueError("unsupported decision")
        return value

    @model_validator(mode="before")
    @classmethod
    def capture_extensions(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        known = set(cls.model_fields)
        extras = {key: value for key, value in data.items() if key not in known and key != "extensions"}
        dangerous = extras.keys() & SAFETY_FIELDS
        if dangerous:
            raise ValueError(f"malformed safety-critical fields: {sorted(dangerous)}")
        if extras:
            merged = dict(data)
            existing = dict(merged.get("extensions") or {})
            existing.update(extras)
            for key in extras:
                merged.pop(key, None)
            merged["extensions"] = existing
            return merged
        return data
