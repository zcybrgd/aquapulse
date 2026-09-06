"""Internal device location context for a future authorized agent contract.

This is not part of Investigation or Response Agent contract 1.0.
device_msisdn is never mapped to operator_contact.
"""

from app.assets.connectivity import device_location_payload, public_zone_id
from app.db.models import Asset


def future_device_context(asset: Asset, *, include_msisdn: bool = False) -> dict:
    """Reserved payload. Callers must not send this on contract 1.0."""
    location = device_location_payload(asset)
    return {
        "device_id": asset.external_id,
        "external_device_alias": (asset.extra_metadata or {}).get("external_alias"),
        "zone_id": location["zone_id"],
        "zone_name": location["zone_name"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "location_label": location["location_label"],
        "device_msisdn": asset.device_msisdn if include_msisdn else None,
        "authorized_msisdn": include_msisdn,
    }


def zone_public_id_from_code(code: str) -> str:
    return public_zone_id(code)
