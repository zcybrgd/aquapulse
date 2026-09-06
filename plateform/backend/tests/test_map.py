from sqlalchemy import func, select

from app.db.models import Asset, PipelineSegment, Zone
from app.db.session import get_session_factory
from app.scripts.seed_database import seed_database


def test_postgis_extension_is_available(client) -> None:
    health = client.get("/api/health").json()
    assert health["postgis"] == "available"
    db_health = client.get("/api/health/database").json()
    assert db_health["postgis"] == "available"


def test_geometry_seed_is_present(test_database) -> None:
    session = get_session_factory()()
    try:
        zones = session.scalar(select(func.count()).select_from(Zone).where(Zone.boundary.is_not(None)))
        pipes = session.scalar(
            select(func.count()).select_from(PipelineSegment).where(PipelineSegment.geometry.is_not(None))
        )
        assets = session.scalar(select(func.count()).select_from(Asset).where(Asset.location.is_not(None)))
        assert zones == 9
        assert pipes == 9
        assert assets == 35
    finally:
        session.close()


def test_map_zones_geojson(client) -> None:
    payload = client.get("/api/map/zones").json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 9
    feature = payload["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "MultiPolygon"
    assert "code" in feature["properties"]
    assert "active_incident_count" in feature["properties"]


def test_map_pipelines_and_assets_geojson(client) -> None:
    pipelines = client.get("/api/map/pipelines").json()
    assets = client.get("/api/map/assets").json()
    assert pipelines["type"] == "FeatureCollection"
    assert assets["type"] == "FeatureCollection"
    assert len(pipelines["features"]) == 9
    assert len(assets["features"]) == 35
    assert pipelines["features"][0]["geometry"]["type"] == "LineString"
    assert assets["features"][0]["geometry"]["type"] == "Point"
    assert len(assets["features"][0]["geometry"]["coordinates"]) == 2


def test_map_incidents_exclude_resolved_by_default(client) -> None:
    active = client.get("/api/map/incidents").json()
    all_incidents = client.get("/api/map/incidents", params={"include_resolved": True}).json()
    assert active["type"] == "FeatureCollection"
    assert len(active["features"]) >= 1
    assert len(all_incidents["features"]) >= len(active["features"])
    statuses = {item["properties"]["status"] for item in active["features"]}
    assert "resolved" not in statuses
    assert "false_alarm" not in statuses


def test_map_summary(client) -> None:
    payload = client.get("/api/map/summary").json()
    assert payload["data_mode"] == "seeded_demo"
    assert payload["visible_zones"] == 9
    assert payload["visible_pipelines"] == 9
    assert payload["visible_assets"] == 35
    assert payload["online"] + payload["degraded"] + payload["offline"] == payload["visible_assets"]
    assert payload["active_incidents"] >= 1
    assert payload["critical_incidents"] >= 1
    assert payload["last_data_update"]


def test_map_zone_filter(client) -> None:
    payload = client.get("/api/map/assets", params={"zone": "Dubai Harbour"}).json()
    ids = {item["id"] for item in payload["features"]}
    assert "SNS-HBR-007" in ids
    assert "SNS-CRN-014" not in ids


def test_map_asset_status_filter(client) -> None:
    payload = client.get("/api/map/assets", params={"asset_status": "offline"}).json()
    assert payload["features"][0]["id"] == "SNS-AIN-220"


def test_map_incident_severity_filter(client) -> None:
    payload = client.get("/api/map/incidents", params={"incident_severity": "tier_3"}).json()
    assert payload["features"]
    assert {item["properties"]["severity"] for item in payload["features"]} == {"tier_3"}


def test_nearby_inside_and_outside_radius(client) -> None:
    inside = client.get(
        "/api/map/nearby",
        params={"latitude": 25.0894, "longitude": 55.1392, "radius_m": 250},
    ).json()
    asset_ids = {item["id"] for item in inside["items"] if item["feature_type"] == "asset"}
    assert "SNS-HBR-007" in asset_ids
    assert all(item["distance_m"] <= 250 for item in inside["items"])

    outside = client.get(
        "/api/map/nearby",
        params={"latitude": 25.0894, "longitude": 55.1392, "radius_m": 80, "feature_type": "asset"},
    ).json()
    far_ids = {item["id"] for item in outside["items"]}
    assert "SNS-CRN-014" not in far_ids


def test_nearby_invalid_coordinates(client) -> None:
    response = client.get("/api/map/nearby", params={"latitude": 100, "longitude": 55.1, "radius_m": 200})
    assert response.status_code == 422


def test_nearby_excessive_radius(client) -> None:
    response = client.get(
        "/api/map/nearby",
        params={"latitude": 25.0894, "longitude": 55.1392, "radius_m": 80_000},
    )
    assert response.status_code == 422


def test_seed_geometry_is_idempotent(test_database) -> None:
    session = get_session_factory()()
    try:
        first = session.execute(select(func.ST_AsGeoJSON(Zone.boundary)).order_by(Zone.code)).scalars().all()
    finally:
        session.close()
    seed_database()
    session = get_session_factory()()
    try:
        second = session.execute(select(func.ST_AsGeoJSON(Zone.boundary)).order_by(Zone.code)).scalars().all()
        assert first == second
        assert len(second) == 9
    finally:
        session.close()


def test_existing_incident_and_asset_apis_remain(client) -> None:
    incident = client.get("/api/incidents/INC-1835").json()
    assert incident["sensor"] == "SNS-HBR-007"
    asset = client.get("/api/assets/SNS-HBR-007").json()
    assert asset["external_id"] == "SNS-HBR-007"
    assert asset["latitude"] == 25.0894
