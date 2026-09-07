"""Normalized Nokia/CAMARA device-network types and helpers.

Network Health does not use an agent. These values describe mobile-network
observations only — they are not incident workflow statuses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from app.db.base import utc_now

ReachabilityStatus = Literal["reachable", "unreachable", "unknown", "not_supported", "not_checked"]
SourceMode = Literal["seeded_demo", "nokia_simulator", "nokia_live"]

REACHABILITY_STATUSES = ("reachable", "unreachable", "unknown", "not_supported", "not_checked")
SOURCE_MODES = ("seeded_demo", "nokia_simulator", "nokia_live")
STALE_FLOOR_SECONDS = 1800

SOURCE_MODE_LABELS = {
    "seeded_demo": "Demonstration data",
    "nokia_simulator": "Nokia simulator",
    "nokia_live": "Nokia live",
}


@dataclass(slots=True)
class ReachabilityResult:
    status: ReachabilityStatus
    reachable_via: str | None = None
    checked_at: datetime | None = None
    subscription_status: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class LocationResult:
    available: bool = False
    latitude: float | None = None
    longitude: float | None = None
    accuracy_radius_m: float | None = None
    area_type: str | None = None
    observed_at: datetime | None = None
    retrieved_at: datetime = field(default_factory=utc_now)
    raw: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class DeviceNetworkProvider(Protocol):
    provider_name: str
    source_mode: SourceMode

    async def get_reachability(self, device_msisdn: str) -> ReachabilityResult: ...

    async def retrieve_location(self, device_msisdn: str) -> LocationResult: ...


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_reachable_via(connectivity: Any) -> str | None:
    if connectivity is None:
        return None
    values: list[str]
    if isinstance(connectivity, str):
        values = [connectivity]
    elif isinstance(connectivity, (list, tuple)):
        values = [str(item) for item in connectivity]
    else:
        return None
    normalized = [item.strip().lower() for item in values if str(item).strip()]
    if "data" in normalized:
        return "data"
    if "sms" in normalized:
        return "sms"
    if normalized:
        return normalized[0]
    return None


def normalize_reachability_payload(payload: dict[str, Any]) -> ReachabilityResult:
    if "subscriptionId" in payload and "reachable" not in payload:
        return ReachabilityResult(
            status="unknown",
            subscription_status=str(payload.get("status") or payload.get("subscriptionStatus") or "active"),
            raw=payload,
            error_code="subscription_response_not_state",
            error_message="Subscription metadata is not the current device reachability state.",
        )
    reachable = payload.get("reachable")
    if reachable is True:
        status: ReachabilityStatus = "reachable"
    elif reachable is False:
        status = "unreachable"
    else:
        status = "unknown"
    return ReachabilityResult(
        status=status,
        reachable_via=normalize_reachable_via(payload.get("connectivity")),
        checked_at=parse_timestamp(payload.get("lastStatusTime") or payload.get("lastStatusDate")),
        raw=payload,
    )


def normalize_location_payload(payload: dict[str, Any]) -> LocationResult:
    area = payload.get("area") if isinstance(payload.get("area"), dict) else {}
    center = area.get("center") if isinstance(area.get("center"), dict) else {}
    latitude = center.get("latitude", payload.get("latitude"))
    longitude = center.get("longitude", payload.get("longitude"))
    radius = area.get("radius", payload.get("accuracy_radius_m") or payload.get("radius"))
    try:
        lat = float(latitude) if latitude is not None else None
        lon = float(longitude) if longitude is not None else None
        accuracy = float(radius) if radius is not None else None
    except (TypeError, ValueError):
        return LocationResult(
            raw=payload,
            error_code="malformed_location",
            error_message="Location response did not contain usable coordinates.",
        )
    if lat is None or lon is None or lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return LocationResult(
            raw=payload,
            error_code="location_unavailable",
            error_message="Network-derived location is not available.",
        )
    if accuracy is not None and accuracy < 0:
        accuracy = None
    return LocationResult(
        available=True,
        latitude=lat,
        longitude=lon,
        accuracy_radius_m=accuracy,
        area_type=area.get("areaType") or payload.get("areaType") or "CIRCLE",
        observed_at=parse_timestamp(payload.get("lastLocationTime")),
        raw=payload,
    )


def configured_source_mode(enabled: bool, mode: str) -> SourceMode:
    normalized = (mode or "mock").strip().lower()
    if enabled and normalized == "live":
        return "nokia_live"
    if normalized in {"simulator", "nokia_simulator"}:
        return "nokia_simulator"
    return "seeded_demo"
