from datetime import timedelta

from sqlalchemy import event

from app.data.incidents import SEED_NOW
from app.db.session import get_engine, get_session_factory
from app.scripts.seed_database import seed_database
from app.scripts.seed_telemetry import expected_seed_reading_count
from app.services.analytics_constants import DEFAULT_INTERVALS, RANGE_DELTAS, SAMPLE_INTERVAL
from app.services.telemetry_constants import SENSOR_SEED_HORIZON
from app.services.telemetry_patterns import reading_values, seed_source_id


def test_analytics_ranges_and_default_buckets(client) -> None:
    for range_key, interval in DEFAULT_INTERVALS.items():
        payload = client.get("/api/analytics/telemetry", params={"range": range_key}).json()
        assert payload["range"] == range_key
        assert payload["interval"] == interval
        assert payload["data_mode"] == "simulated"
        assert payload["start"] < payload["end"]
        delta = RANGE_DELTAS[range_key]
        assert payload["filters"]["interval"] == interval


def test_custom_valid_interval(client) -> None:
    payload = client.get("/api/analytics/telemetry", params={"range": "24h", "interval": "1h"}).json()
    assert payload["interval"] == "1h"
    assert len(payload["series"]) >= 24


def test_invalid_range_and_interval(client) -> None:
    invalid_range = client.get("/api/analytics/overview", params={"range": "1h"})
    assert invalid_range.status_code == 422
    assert invalid_range.json()["detail"]["code"] == "invalid_analytics_range"

    invalid_interval = client.get("/api/analytics/telemetry", params={"range": "24h", "interval": "raw"})
    assert invalid_interval.status_code == 422
    assert invalid_interval.json()["detail"]["code"] == "invalid_analytics_interval"


def test_unknown_zone_and_sensor(client) -> None:
    zone = client.get("/api/analytics/overview", params={"zone": "Unknown DMA"})
    assert zone.status_code == 404
    assert zone.json()["detail"]["code"] == "zone_not_found"

    sensor = client.get("/api/analytics/telemetry", params={"sensor": "SNS-MISSING"})
    assert sensor.status_code == 404
    assert sensor.json()["detail"]["code"] == "asset_not_found"


def test_zone_and_sensor_filters(client) -> None:
    harbour = client.get("/api/analytics/telemetry", params={"range": "24h", "zone": "Dubai Harbour"}).json()
    assert harbour["reporting_sensors"] >= 1
    assert harbour["selected_sensors"] == 2

    single = client.get(
        "/api/analytics/telemetry",
        params={"range": "24h", "sensor": "SNS-HBR-007"},
    ).json()
    assert single["selected_sensors"] == 1
    assert single["reporting_sensors"] == 1
    assert single["summary"]["estimated_monitored_volume"]["current"] is not None


def test_previous_period_comparison(client) -> None:
    payload = client.get("/api/analytics/overview", params={"range": "24h"}).json()
    pressure = next(item for item in payload["kpis"] if item["key"] == "average_pressure")
    assert pressure["current"] is not None
    assert pressure["previous"] is not None
    assert pressure["trend"] in {"up", "down", "stable"}
    assert pressure["change"] is not None

    month = client.get("/api/analytics/overview", params={"range": "30d"}).json()
    month_pressure = next(item for item in month["kpis"] if item["key"] == "average_pressure")
    assert month_pressure["current"] is not None
    assert month_pressure["previous"] is None
    assert month_pressure["trend"] == "unavailable"


def test_flow_integration_and_completeness(client) -> None:
    payload = client.get("/api/analytics/telemetry", params={"range": "24h", "sensor": "SNS-HBR-007"}).json()
    volume = payload["summary"]["estimated_monitored_volume"]["current"]
    assert volume is not None and volume > 0
    completeness = payload["summary"]["telemetry_completeness"]["current"]
    assert completeness == 100.0
    assert payload["stale_sensors"] == 0
    assert payload["offline_sensors"] == 0


def test_offline_sensor_freshness(client) -> None:
    payload = client.get("/api/analytics/telemetry", params={"range": "24h", "sensor": "SNS-AIN-220"}).json()
    assert payload["offline_sensors"] == 1
    assert payload["selected_sensors"] == 1
    assert payload["summary"]["average_pressure"]["current"] is not None


def test_network_fresh_stale_offline_counts(client) -> None:
    payload = client.get("/api/analytics/telemetry", params={"range": "24h"}).json()
    assert payload["selected_sensors"] == 16
    assert payload["offline_sensors"] == 1
    assert payload["reporting_sensors"] >= 15
    assert payload["stale_sensors"] == 0


def test_detection_and_incident_distributions(client) -> None:
    detections = client.get("/api/analytics/detections", params={"range": "24h"}).json()
    assert detections["created"]["current"] is not None
    assert detections["created"]["current"] >= 0
    assert detections["promotion_rate"]["unit"] == "%"
    assert isinstance(detections["by_priority"], list)
    assert isinstance(detections["by_rule"], list)

    incidents = client.get("/api/analytics/incidents", params={"range": "24h"}).json()
    assert incidents["created"]["current"] == 9
    assert {item["key"] for item in incidents["by_severity"]} <= {"tier_1", "tier_2", "tier_3"}
    assert incidents["by_classification"]
    assert incidents["false_alarms"]["current"] == 1
    assert incidents["resolved"]["current"] == 1


def test_response_durations_and_nulls(client) -> None:
    operations = client.get("/api/analytics/operations", params={"range": "24h"}).json()
    assert operations["mean_acknowledgement_minutes"]["current"] is not None
    assert operations["mean_response_start_minutes"]["current"] is not None
    assert operations["open_response_tasks"]["current"] >= 1
    assert operations["overdue_response_tasks"]["current"] >= 1

    previous_month = client.get("/api/analytics/operations", params={"range": "30d"}).json()
    assert previous_month["mean_acknowledgement_minutes"]["previous"] is None
    assert previous_month["mean_acknowledgement_minutes"]["trend"] == "unavailable"


def test_zone_analytics(client) -> None:
    payload = client.get("/api/analytics/zones", params={"range": "24h"}).json()
    names = {item["zone"] for item in payload["items"]}
    assert "Dubai Harbour" in names
    harbour = next(item for item in payload["items"] if item["zone"] == "Dubai Harbour")
    assert harbour["sufficient_data"] is True
    assert harbour["reporting_sensors"] >= 1
    assert harbour["average_pressure_bar"] is not None


def test_empty_period_does_not_coerce_null_to_zero(client) -> None:
    payload = client.get("/api/analytics/telemetry", params={"range": "30d"}).json()
    volume = payload["summary"]["estimated_monitored_volume"]
    assert volume["previous"] is None
    assert volume["change"] is None


def test_thirty_day_deterministic_seed(test_database) -> None:
    expected = expected_seed_reading_count()
    session = get_session_factory()()
    try:
        from sqlalchemy import text

        count = session.execute(text("SELECT COUNT(*) FROM sensor_readings WHERE source_message_id LIKE 'seed:%'")).scalar()
        distinct = session.execute(
            text("SELECT COUNT(DISTINCT source_message_id) FROM sensor_readings WHERE source_message_id LIKE 'seed:%'")
        ).scalar()
        earliest = session.execute(text("SELECT MIN(time) FROM sensor_readings")).scalar()
        latest = session.execute(text("SELECT MAX(time) FROM sensor_readings WHERE source_message_id LIKE 'seed:%'")).scalar()
        assert count == expected
        assert distinct == expected
        assert earliest <= SEED_NOW - SENSOR_SEED_HORIZON + SAMPLE_INTERVAL
        assert latest == SEED_NOW
    finally:
        session.close()


def test_last_24h_pattern_preserved(test_database) -> None:
    session = get_session_factory()()
    try:
        from sqlalchemy import text

        when = SEED_NOW - timedelta(hours=12)
        source_id = seed_source_id("SNS-HBR-007", when)
        row = session.execute(
            text(
                "SELECT pressure_kpa, flow_lps, source_message_id FROM sensor_readings "
                "WHERE source_message_id = :source"
            ),
            {"source": source_id},
        ).one()
        expected = reading_values("SNS-HBR-007", when, "online")
        assert row.pressure_kpa == expected["pressure_kpa"]
        assert row.flow_lps == expected["flow_lps"]
        assert row.source_message_id == source_id
    finally:
        session.close()


def test_seed_idempotency_after_analytics_horizon(test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.sensor_readings == second.sensor_readings
    assert first.sensor_readings >= expected_seed_reading_count()
    assert first.incidents == second.incidents == 9
    assert first.timeline_events == second.timeline_events == 69


def test_overview_query_count_is_bounded(test_database) -> None:
    from app.services.analytics import AnalyticsService

    session = get_session_factory()()
    engine = get_engine()
    queries: list[str] = []

    def before_cursor(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor)
    try:
        AnalyticsService(session).overview("24h")
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)
        session.close()
    assert 0 < len(queries) <= 30


def test_existing_apis_remain_compatible(client) -> None:
    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert "active_incidents" in body
    assert "overdue_response_tasks" in body

    incidents = client.get("/api/incidents")
    assert incidents.status_code == 200
    assert incidents.json()["total"] == 9

    detections = client.get("/api/detections")
    assert detections.status_code == 200

    telemetry = client.get("/api/telemetry/network/summary")
    assert telemetry.status_code == 200


def test_promoted_detection_appears_in_incident_analytics(client) -> None:
    incidents = client.get("/api/analytics/incidents", params={"range": "7d"}).json()
    assert incidents["created"]["current"] == 9
    detections = client.get("/api/analytics/detections", params={"range": "7d"}).json()
    assert detections["promoted"]["current"] >= 0


def test_analytics_envelope_and_simulated_label(client) -> None:
    for path in (
        "/api/analytics/overview",
        "/api/analytics/telemetry",
        "/api/analytics/zones",
        "/api/analytics/detections",
        "/api/analytics/incidents",
        "/api/analytics/operations",
        "/api/analytics/assets",
    ):
        payload = client.get(path, params={"range": "24h"}).json()
        assert payload["data_mode"] == "simulated"
        assert payload["range"] == "24h"
        assert "filters" in payload
        assert payload["start"]
        assert payload["end"]
        assert payload["generated_at"]
