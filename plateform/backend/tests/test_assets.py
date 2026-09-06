from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.data.assets import get_asset_catalog
from app.db.models import Asset, Incident
from app.db.session import get_session_factory
from app.scripts.seed_database import seed_database

EXPECTED_ASSETS = len(get_asset_catalog())


def test_asset_list(client) -> None:
    response = client.get("/api/assets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == EXPECTED_ASSETS
    assert payload["summary"]["total_assets"] == EXPECTED_ASSETS
    assert payload["summary"]["online"] >= 1
    assert payload["summary"]["degraded"] >= 1
    assert payload["summary"]["offline"] >= 1
    assert payload["summary"]["maintenance_due"] >= 1
    assert payload["items"][0]["id"] == payload["items"][0]["external_id"]
    assert "uuid" not in payload["items"][0]["id"].lower()


def test_asset_detail_preserves_incident_sensor(client) -> None:
    response = client.get("/api/assets/SNS-HBR-007")
    assert response.status_code == 200
    payload = response.json()
    assert payload["external_id"] == "SNS-HBR-007"
    assert payload["asset_type"] == "sensor"
    assert payload["zone"] == "Dubai Harbour"
    assert payload["sensor"] is not None
    assert payload["valve"] is None
    assert payload["gateway"] is None
    assert "pressure" in payload["sensor"]["measurement_types"]
    numbers = {item["incident_number"] for item in payload["related_incidents"]}
    assert "INC-1835" in numbers


def test_valve_and_gateway_detail(client) -> None:
    valve = client.get("/api/assets/VLV-CRN-014").json()
    assert valve["asset_type"] == "valve"
    assert valve["valve"]["current_position"] == "closed"
    assert valve["valve"]["control_mode"] == "remote"
    assert valve["sensor"] is None

    gateway = client.get("/api/assets/HBR-GW-02").json()
    assert gateway["asset_type"] == "gateway"
    assert gateway["gateway"]["provider"] == "du"
    assert "LoRaWAN" in gateway["gateway"]["protocols"]


def test_asset_related_incidents(client) -> None:
    response = client.get("/api/assets/SNS-CRN-014/incidents")
    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_id"] == "SNS-CRN-014"
    assert payload["total"] >= 1
    assert payload["items"][0]["incident_number"] == "INC-1842"


def test_valve_health_series_is_mock(client) -> None:
    response = client.get("/api/assets/VLV-CRN-014/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["series_kind"] == "mock_recent_health"
    assert "not live" in payload["note"].lower() or "mock_recent_health" in payload["note"].lower()
    assert len(payload["items"]) == 12
    timestamps = [point["timestamp"] for point in payload["items"]]
    assert timestamps == sorted(timestamps)


def test_unknown_asset(client) -> None:
    response = client.get("/api/assets/SENSOR-NONE")
    assert response.status_code == 404
    assert response.json()["detail"] == {"message": "Asset not found", "code": "asset_not_found"}


def test_asset_type_filter(client) -> None:
    response = client.get("/api/assets", params={"asset_type": "gateway"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 9
    assert {item["asset_type"] for item in payload["items"]} == {"gateway"}


def test_status_filter(client) -> None:
    response = client.get("/api/assets", params={"status": "offline"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["external_id"] == "SNS-AIN-220"


def test_zone_filter(client) -> None:
    response = client.get("/api/assets", params={"zone": "Dubai Harbour"})
    assert response.status_code == 200
    ids = {item["external_id"] for item in response.json()["items"]}
    assert "SNS-HBR-007" in ids
    assert "HBR-GW-02" in ids
    assert "SNS-CRN-014" not in ids


def test_asset_search(client) -> None:
    by_serial = client.get("/api/assets", params={"search": "SI-HBR-007-2023"})
    assert by_serial.json()["total"] == 1
    assert by_serial.json()["items"][0]["external_id"] == "SNS-HBR-007"

    by_maker = client.get("/api/assets", params={"search": "Kerlink"})
    assert by_maker.json()["total"] >= 3


def test_asset_sort_health_asc(client) -> None:
    response = client.get("/api/assets", params={"sort_by": "health_score", "sort_order": "asc"})
    scores = [item["health_score"] for item in response.json()["items"] if item["health_score"] is not None]
    assert scores == sorted(scores)
    assert response.json()["items"][0]["external_id"] == "SNS-AIN-220"


def test_unsupported_sort_is_rejected(client) -> None:
    response = client.get("/api/assets", params={"sort_by": "not_a_field"})
    assert response.status_code == 422


def test_summary_statistics(client) -> None:
    payload = client.get("/api/assets").json()["summary"]
    assert payload["online"] + payload["degraded"] + payload["offline"] == payload["total_assets"]
    sensors = client.get("/api/assets", params={"asset_type": "sensor"}).json()
    assert sensors["total"] == 16


def test_dashboard_sensor_counts_come_from_assets(client) -> None:
    dashboard = client.get("/api/dashboard/summary").json()
    sensors = client.get("/api/assets", params={"asset_type": "sensor"}).json()["items"]
    assert dashboard["total_sensors"] == 16
    assert dashboard["online_sensors"] == sum(1 for item in sensors if item["operational_status"] == "online")
    assert dashboard["total_sensors"] != 148


def test_incident_relationships_preserved(client) -> None:
    incident = client.get("/api/incidents/INC-1835").json()
    assert incident["sensor"] == "SNS-HBR-007"
    assert incident["associated_valve"] == "VLV-HBR-007"
    valve_incidents = client.get("/api/assets/VLV-HBR-007/incidents").json()
    assert "INC-1835" in {item["incident_number"] for item in valve_incidents["items"]}


def test_check_constraints_reject_invalid_asset_values(test_database) -> None:
    cases = [
        ("battery_pct", 140),
        ("health_score", -1),
        ("sampling_interval_seconds", 0),
        ("latitude", 91),
        ("longitude", 181),
        ("asset_type", "pump"),
        ("current_position", "halfway"),
        ("control_mode", "scheduled"),
    ]
    for field, value in cases:
        session = get_session_factory()()
        try:
            existing = session.scalar(select(Asset).limit(1))
            assert existing is not None
            setattr(existing, field, value)
            with pytest.raises(IntegrityError):
                session.commit()
        finally:
            session.rollback()
            session.close()


def test_unique_serial_number_constraint(test_database) -> None:
    session = get_session_factory()()
    try:
        existing = session.scalar(select(Asset).where(Asset.serial_number.is_not(None)).limit(1))
        assert existing is not None
        clone = Asset(
            id=uuid4(),
            organization_id=existing.organization_id,
            zone_id=existing.zone_id,
            external_id="SNS-DUP-SERIAL",
            name="Duplicate serial",
            asset_type="sensor",
            operational_status="online",
            serial_number=existing.serial_number,
        )
        session.add(clone)
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_seed_asset_count_is_idempotent(test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.assets == second.assets == EXPECTED_ASSETS
    assert first.incidents == second.incidents == 9
