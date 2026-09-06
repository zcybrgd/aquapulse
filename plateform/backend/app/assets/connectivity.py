"""Device location and cellular identity helpers.

device_msisdn is a device SIM identity. It is not an operator_contact.
"""

from __future__ import annotations

import re

from app.core.exceptions import AssetValidationError
from app.db.models import Asset, PipelineSegment, Zone

E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")
LOCATION_LABEL_MAX = 160


def public_zone_id(code: str) -> str:
    return f"ZONE-{code.strip().upper()}"


def normalize_device_msisdn(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    compact = re.sub(r"[\s\-().]", "", trimmed)
    if not E164_PATTERN.fullmatch(compact) or len(compact) > 16:
        raise AssetValidationError(
            "Device MSISDN must be an E.164 number such as +971500004821.",
            code="invalid_device_msisdn",
        )
    return compact


def mask_device_msisdn(value: str | None) -> str | None:
    if not value:
        return None
    digits = value[1:] if value.startswith("+") else value
    if len(digits) <= 4:
        return value
    prefix_len = min(3, max(1, len(digits) - 4))
    hidden = len(digits) - prefix_len - 4
    return f"+{digits[:prefix_len]}{'•' * hidden}{digits[-4:]}"


def normalize_location_label(value: str | None) -> str | None:
    if value is None:
        return None
    label = " ".join(value.split())
    if not label:
        return None
    if len(label) > LOCATION_LABEL_MAX:
        raise AssetValidationError(
            f"Location label must be at most {LOCATION_LABEL_MAX} characters.",
            code="invalid_location_label",
        )
    return label


def require_direct_zone(asset: Asset) -> Zone:
    if asset.zone is None or asset.zone_id is None:
        raise AssetValidationError(
            f"Asset {asset.external_id} is missing a direct zone.",
            code="asset_zone_required",
        )
    return asset.zone


def assert_zone_segment_consistent(asset: Asset, segment: PipelineSegment | None = None) -> None:
    zone = require_direct_zone(asset)
    linked = segment if segment is not None else asset.pipeline_segment
    if linked is None:
        return
    if linked.zone_id != zone.id:
        raise AssetValidationError(
            f"Asset {asset.external_id} zone does not match its pipeline segment zone.",
            code="asset_zone_segment_mismatch",
        )


def device_location_payload(asset: Asset) -> dict:
    zone = require_direct_zone(asset)
    return {
        "zone_id": public_zone_id(zone.code),
        "zone_name": zone.name,
        "location_label": asset.location_label,
        "latitude": asset.latitude,
        "longitude": asset.longitude,
    }
