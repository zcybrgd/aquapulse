"""Idempotent demonstration device-network snapshots.

Stored in PostgreSQL only. React must not hardcode these records.
Network Health does not use an agent.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.db.models import Asset
from app.db.models.device_network import DeviceNetworkSnapshot

SEED_SNAPSHOTS: list[dict] = [
    {
        "public_id": "DNS-000001",
        "asset_id": "HBR-GW-02",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "reachable",
        "reachable_via": "data",
        "location": True,
        "accuracy_radius_m": 420.0,
        "location_area_type": "CIRCLE",
        "offset_m": (0.0012, 0.0009),
        "age": timedelta(minutes=8),
    },
    {
        "public_id": "DNS-000002",
        "asset_id": "CRN-GW-01",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "reachable",
        "reachable_via": "sms",
        "location": True,
        "accuracy_radius_m": 780.0,
        "location_area_type": "CIRCLE",
        "offset_m": (-0.0008, 0.0011),
        "age": timedelta(minutes=12),
    },
    {
        "public_id": "DNS-000003",
        "asset_id": "SNS-HBR-007",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "unreachable",
        "reachable_via": None,
        "location": False,
        "age": timedelta(minutes=18),
    },
    {
        "public_id": "DNS-000004",
        "asset_id": "SNS-AIN-221",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "unknown",
        "reachable_via": None,
        "location": True,
        "accuracy_radius_m": 1100.0,
        "location_area_type": "CIRCLE",
        "offset_m": (0.0015, -0.001),
        "age": timedelta(minutes=22),
    },
    {
        "public_id": "DNS-000005",
        "asset_id": "VLV-CRN-014",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "not_supported",
        "reachable_via": None,
        "location": False,
        "error_code": "msisdn_required",
        "error_message": "This device has no cellular identity, so Nokia APIs cannot be used.",
        "age": timedelta(minutes=6),
    },
    {
        "public_id": "DNS-000006",
        "asset_id": "DOH-GW-02",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "reachable",
        "reachable_via": "data",
        "location": True,
        "accuracy_radius_m": 850.0,
        "location_area_type": "CIRCLE",
        "offset_m": (0.0006, 0.0004),
        "age": timedelta(minutes=15),
    },
    {
        "public_id": "DNS-000007",
        "asset_id": "JED-GW-01",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "reachable",
        "reachable_via": "data",
        "location": False,
        "age": timedelta(minutes=20),
    },
    {
        "public_id": "DNS-000008",
        "asset_id": "MCT-GW-01",
        "provider": "nokia_mock",
        "source_mode": "nokia_simulator",
        "reachability_status": "unknown",
        "reachable_via": None,
        "location": False,
        "error_code": "nokia_simulator_error",
        "error_message": "Nokia simulator rejected the reachability request.",
        "age": timedelta(minutes=9),
    },
    {
        "public_id": "DNS-000009",
        "asset_id": "AIN-GW-01",
        "provider": "nokia_mock",
        "source_mode": "seeded_demo",
        "reachability_status": "reachable",
        "reachable_via": "data",
        "location": True,
        "accuracy_radius_m": 960.0,
        "location_area_type": "CIRCLE",
        "offset_m": (0.001, -0.0007),
        "age": timedelta(hours=6),
    },
]


def _upsert(session: Session, asset: Asset, spec: dict, now) -> DeviceNetworkSnapshot:
    retrieved_at = now - spec["age"]
    available = bool(spec["location"])
    offset = spec.get("offset_m") or (0.0, 0.0)
    latitude = (asset.latitude or 0) + offset[0] if available else None
    longitude = (asset.longitude or 0) + offset[1] if available else None
    values = {
        "asset_id": asset.id,
        "provider": spec["provider"],
        "source_mode": spec["source_mode"],
        "reachability_status": spec["reachability_status"],
        "reachable_via": spec["reachable_via"],
        "reachability_checked_at": retrieved_at,
        "network_location_available": available,
        "network_latitude": latitude,
        "network_longitude": longitude,
        "accuracy_radius_m": spec.get("accuracy_radius_m") if available else None,
        "location_area_type": spec.get("location_area_type") if available else None,
        "location_observed_at": retrieved_at if available else None,
        "retrieved_at": retrieved_at,
        "request_correlation_id": f"seed-{spec['public_id'].lower()}",
        "raw_reachability_payload": {"seeded": True, "status": spec["reachability_status"]},
        "raw_location_payload": {"seeded": True, "available": available},
        "error_code": spec.get("error_code"),
        "error_message": spec.get("error_message"),
    }
    row = session.scalar(
        select(DeviceNetworkSnapshot).where(DeviceNetworkSnapshot.public_id == spec["public_id"])
    )
    if row is None:
        row = DeviceNetworkSnapshot(public_id=spec["public_id"], **values)
        session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    return row


def seed_device_network(session: Session) -> dict[str, int]:
    now = utc_now()
    written = 0
    for spec in SEED_SNAPSHOTS:
        asset = session.scalar(select(Asset).where(Asset.external_id == spec["asset_id"]))
        if asset is None:
            raise RuntimeError(f"device network seed missing asset {spec['asset_id']}")
        _upsert(session, asset, spec, now)
        written += 1
    session.flush()
    return {"snapshots": len(SEED_SNAPSHOTS), "written": written}
