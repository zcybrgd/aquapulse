from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import TelemetryValidationError
from app.data.incidents import SEED_NOW
from app.db.models import SensorReading
from app.db.session import get_session_factory, timescaledb_is_available
from app.scripts.seed_database import seed_database
from app.scripts.seed_telemetry import expected_seed_reading_count
from app.schemas.telemetry import IngestReading
from app.services.telemetry import TelemetryService, classify_freshness
from app.services.telemetry_constants import FRESH_AFTER, STALE_AFTER


def test_timescaledb_extension_available(client) -> None:
    assert timescaledb_is_available() is True
    health = client.get("/api/health").json()
    assert health["timescaledb"] == "available"
    assert health["postgis"] == "available"
    db_health = client.get("/api/health/database").json()
    assert db_health["timescaledb"] == "available"


def test_sensor_readings_is_hypertable(test_database) -> None:
    session = get_session_factory()()
    try:
        name = session.execute(
            text(
                "SELECT hypertable_name FROM timescaledb_information.hypertables "
                "WHERE hypertable_name = 'sensor_readings'"
            )
        ).scalar()
        assert name == "sensor_readings"
    finally:
        session.close()


def test_historical_seed_count_and_idempotency(test_database) -> None:
    expected = expected_seed_reading_count()
    first = seed_database()
    second = seed_database()
    assert first.sensor_readings == second.sensor_readings
    assert first.telemetry_points == second.telemetry_points == 144
    session = get_session_factory()()
    try:
        seed_rows = session.execute(
            text("SELECT COUNT(*) FROM sensor_readings WHERE source_message_id LIKE 'seed:%'")
        ).scalar()
        seed_sources = session.execute(
            text("SELECT COUNT(DISTINCT source_message_id) FROM sensor_readings WHERE source_message_id LIKE 'seed:%'")
        ).scalar()
        assert seed_rows == expected
        assert seed_sources == expected
    finally:
        session.close()


def test_composite_primary_key_rejects_duplicate_time(test_database) -> None:
    session = get_session_factory()()
    try:
        existing = session.scalar(select(SensorReading).limit(1))
        assert existing is not None
        try:
            session.execute(
                text(
                    "INSERT INTO sensor_readings "
                    "(time, sensor_id, organization_id, source_message_id, pressure_kpa, received_at, quality_flags) "
                    "VALUES (:time, :sensor_id, :organization_id, :source_message_id, 401, :received_at, 0)"
                ),
                {
                    "time": existing.time,
                    "sensor_id": existing.sensor_id,
                    "organization_id": existing.organization_id,
                    "source_message_id": f"{existing.source_message_id}-dup-time",
                    "received_at": existing.received_at,
                },
            )
            session.commit()
            raise AssertionError("duplicate (sensor_id, time) was accepted")
        except IntegrityError:
            session.rollback()
    finally:
        session.close()


def test_source_message_deduplication(test_database) -> None:
    session = get_session_factory()()
    try:
        service = TelemetryService(session)
        when = datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=uuid4().int % 10_000_000)
        payload = IngestReading(
            sensor_external_id="SNS-HBR-007",
            time=when,
            source_message_id=f"test-dedup-hbr-007-{uuid4()}",
            pressure_kpa=410.0,
            received_at=when,
        )
        first = service.ingest(payload)
        second = service.ingest(payload)
        assert first.status == "inserted"
        assert second.status == "duplicate"
    finally:
        session.close()


def test_invalid_percentage_and_empty_payload_rejected(test_database) -> None:
    session = get_session_factory()()
    try:
        service = TelemetryService(session)
        when = datetime.now(timezone.utc)
        try:
            service.ingest(
                IngestReading(
                    sensor_external_id="SNS-HBR-007",
                    time=when,
                    source_message_id="test-bad-battery",
                    battery_pct=140,
                    received_at=when,
                )
            )
            raise AssertionError("invalid battery was accepted")
        except TelemetryValidationError as exc:
            assert exc.code == "invalid_percentage"
        try:
            service.ingest(
                IngestReading(
                    sensor_external_id="SNS-HBR-007",
                    time=when,
                    source_message_id="test-empty",
                    received_at=when,
                )
            )
            raise AssertionError("empty payload was accepted")
        except TelemetryValidationError as exc:
            assert exc.code == "no_measurements"
    finally:
        session.close()


def test_non_sensor_rejected(test_database) -> None:
    session = get_session_factory()()
    try:
        service = TelemetryService(session)
        when = datetime.now(timezone.utc)
        try:
            service.ingest(
                IngestReading(
                    sensor_external_id="VLV-CRN-014",
                    time=when,
                    source_message_id="test-valve",
                    pressure_kpa=400,
                    received_at=when,
                )
            )
            raise AssertionError("valve ingest was accepted")
        except TelemetryValidationError as exc:
            assert exc.code == "not_a_sensor"
    finally:
        session.close()


def test_latest_and_freshness_classification(client, test_database) -> None:
    latest = client.get("/api/telemetry/sensors/SNS-HBR-007/latest").json()
    assert latest["sensor_id"] == "SNS-HBR-007"
    assert latest["time"] is not None
    assert latest["data_mode"] == "simulated"
    assert latest["freshness"] in {"fresh", "stale", "offline"}

    now = SEED_NOW
    assert classify_freshness(now - timedelta(minutes=5), now) == "fresh"
    assert classify_freshness(now - FRESH_AFTER - timedelta(minutes=1), now) == "stale"
    assert classify_freshness(now - STALE_AFTER - timedelta(minutes=1), now) == "offline"
    assert classify_freshness(None, now) == "offline"

    offline = client.get("/api/telemetry/sensors/SNS-AIN-220/latest").json()
    assert offline["sensor_id"] == "SNS-AIN-220"
    assert offline["freshness"] == "offline"


def test_raw_and_aggregated_history(client) -> None:
    raw = client.get(
        "/api/telemetry/sensors/SNS-HBR-007",
        params={
            "start": (SEED_NOW - timedelta(hours=2)).isoformat(),
            "end": SEED_NOW.isoformat(),
            "interval": "raw",
            "limit": 50,
        },
    ).json()
    assert raw["interval"] == "raw"
    assert raw["data_mode"] == "simulated"
    assert raw["total"] >= 10
    times = [item["time"] for item in raw["items"]]
    assert times == sorted(times)

    bucketed = client.get(
        "/api/telemetry/sensors/SNS-HBR-007",
        params={
            "start": (SEED_NOW - timedelta(hours=6)).isoformat(),
            "end": SEED_NOW.isoformat(),
            "interval": "1h",
            "metrics": "pressure,flow",
        },
    ).json()
    assert bucketed["interval"] == "1h"
    assert bucketed["total"] >= 1
    assert bucketed["items"][0]["pressure_kpa"] is not None


def test_range_metric_and_limit_validation(client) -> None:
    bad_range = client.get("/api/telemetry/sensors/SNS-HBR-007", params={"range": "2d"})
    assert bad_range.status_code == 422

    too_wide = client.get(
        "/api/telemetry/sensors/SNS-HBR-007",
        params={
            "start": (SEED_NOW - timedelta(days=10)).isoformat(),
            "end": SEED_NOW.isoformat(),
        },
    )
    assert too_wide.status_code == 422
    assert too_wide.json()["detail"]["code"] == "range_too_large"

    bad_metric = client.get(
        "/api/telemetry/sensors/SNS-HBR-007",
        params={"range": "1h", "metrics": "not_a_metric"},
    )
    assert bad_metric.status_code == 422
    assert bad_metric.json()["detail"]["code"] == "invalid_metrics"

    limited = client.get(
        "/api/telemetry/sensors/SNS-HBR-007",
        params={
            "start": (SEED_NOW - timedelta(hours=24)).isoformat(),
            "end": SEED_NOW.isoformat(),
            "interval": "raw",
            "limit": 7,
        },
    ).json()
    assert limited["total"] == 7


def test_network_summary(client) -> None:
    payload = client.get("/api/telemetry/network/summary").json()
    assert payload["sensor_count"] == 16
    assert payload["data_mode"] == "simulated"
    assert payload["fresh_sensors"] + payload["stale_sensors"] + payload["offline_sensors"] == 16
    assert payload["last_telemetry_at"]


def test_dashboard_telemetry_from_database(client) -> None:
    payload = client.get("/api/dashboard/telemetry", params={"range": "24h"}).json()
    assert payload["data_mode"] == "simulated"
    assert payload["range"] == "24h"
    assert len(payload["readings"]) >= 1
    reading = payload["readings"][0]
    assert "pressure" in reading
    assert "flow_rate" in reading
    assert "packet_loss" in reading
    assert 3.0 < reading["pressure"] < 5.5
    assert reading["flow_rate"] > 0


def test_sensor_health_uses_timescaledb(client) -> None:
    payload = client.get("/api/assets/SNS-HBR-007/health", params={"range": "24h"}).json()
    assert payload["series_kind"] == "sensor_readings"
    assert payload["data_mode"] == "simulated"
    assert len(payload["items"]) >= 1
    assert payload["items"][0]["pressure_kpa"] is not None


def test_valve_health_remains_mock(client) -> None:
    payload = client.get("/api/assets/VLV-CRN-014/health").json()
    assert payload["series_kind"] == "mock_recent_health"
    assert "mock_recent_health" in payload["data_mode"]
    assert len(payload["items"]) == 12


def test_map_sensor_telemetry_properties(client) -> None:
    payload = client.get("/api/map/assets").json()
    harbour = next(item for item in payload["features"] if item["id"] == "SNS-HBR-007")
    assert harbour["properties"]["latest_reading_at"]
    assert harbour["properties"]["telemetry_freshness"] in {"fresh", "stale", "offline"}
    offline = next(item for item in payload["features"] if item["id"] == "SNS-AIN-220")
    assert offline["properties"]["telemetry_freshness"] == "offline"


def test_existing_incident_and_asset_apis(client) -> None:
    incident = client.get("/api/incidents/INC-1835").json()
    assert incident["incident_number"] == "INC-1835"
    asset = client.get("/api/assets/SNS-HBR-007").json()
    assert asset["external_id"] == "SNS-HBR-007"
    health = client.get("/api/health").json()
    assert health["postgis"] == "available"
    assert health["timescaledb"] == "available"
