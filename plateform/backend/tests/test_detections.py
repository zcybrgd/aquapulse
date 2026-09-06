from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select, update

from app.db.models import (
    AnomalyDetection,
    DetectionEvidence,
    DetectionInvestigationEvent,
    DetectionRule,
    Incident,
    SensorReading,
)
from app.db.models.integration import AgentFinding
from app.db.session import get_session_factory
from app.detection.catalog import RULE_CATALOG
from app.detection.engine import DetectionEngine
from app.schemas.telemetry import IngestReading
from app.scripts.seed_database import seed_database
from app.scripts.seed_rules import seed_detection_rules
from app.services.telemetry import TelemetryService
from app.services.telemetry_patterns import scenario_reading_values


_HORIZON = datetime(2031, 1, 1, tzinfo=timezone.utc)
_HORIZON_STEP = 0


def _unique_end() -> datetime:
    global _HORIZON_STEP
    _HORIZON_STEP += 1
    jitter = int(uuid4().hex[:8], 16) % 50_000
    return datetime(2035, 6, 1, tzinfo=timezone.utc) + timedelta(hours=_HORIZON_STEP * 12, seconds=jitter)


def _session():
    return get_session_factory()()


def _cleanup_detections() -> None:
    session = _session()
    try:
        session.execute(delete(DetectionInvestigationEvent))
        rows = list(session.scalars(select(AnomalyDetection)).all())
        for row in rows:
            row.status = "new"
            row.incident_id = None
            row.merged_into_detection_id = None
            row.dismissal_reason = None
        session.flush()
        session.execute(update(AgentFinding).values(anomaly_detection_id=None))
        session.execute(delete(DetectionEvidence))
        session.execute(delete(AnomalyDetection))
        session.execute(delete(SensorReading).where(SensorReading.time >= _HORIZON))
        session.commit()
    finally:
        session.close()


def _ingest_scenario(sensor_id: str, scenario: str, count: int, end: datetime, spacing_minutes: float = 3) -> None:
    session = _session()
    try:
        service = TelemetryService(session)
        token = uuid4().hex[:8]
        for step in range(count):
            when = end - timedelta(minutes=spacing_minutes * (count - 1 - step))
            when = when.replace(microsecond=int(token[:6], 16) % 1000 + step)
            values = scenario_reading_values(
                sensor_id,
                when,
                "online",
                scenario=scenario,
                step=step,
                total_steps=count,
            )
            if values is None:
                continue
            service.ingest(
                IngestReading(
                    sensor_external_id=sensor_id,
                    time=when,
                    source_message_id=f"test:{token}:{step}",
                    received_at=when,
                    raw_payload={"origin": "test", "scenario": scenario},
                    **values,
                )
            )
    finally:
        session.close()


def test_rule_seed_idempotent(test_database) -> None:
    session = _session()
    try:
        first = seed_detection_rules(session)
        session.commit()
        second = seed_detection_rules(session)
        session.commit()
        count = session.scalar(select(func.count()).select_from(DetectionRule))
        codes = list(session.scalars(select(DetectionRule.code).order_by(DetectionRule.code)).all())
        assert first == len(RULE_CATALOG)
        assert second == len(RULE_CATALOG)
        assert count == len(RULE_CATALOG)
        assert codes == sorted(item["code"] for item in RULE_CATALOG)
        versions = list(session.scalars(select(DetectionRule.version)).all())
        assert set(versions) == {1}
    finally:
        session.close()


def test_normal_scenario_no_rate_detection(test_database, client) -> None:
    _cleanup_detections()
    end = _unique_end()
    _ingest_scenario("SNS-HBR-007", "normal", 10, end)
    session = _session()
    try:
        summary = DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            rule_code="PRESSURE_DROP",
            now=end + timedelta(seconds=30),
        )
        assert summary.detections_created == 0
        assert summary.errors == 0
    finally:
        session.close()
    assert client.get("/api/incidents").json()["total"] == 9


def test_combined_and_persistence_and_dedup(test_database, client) -> None:
    _cleanup_detections()
    incident_count = client.get("/api/incidents").json()["total"]
    end = _unique_end()
    _ingest_scenario("SNS-HBR-007", "combined_leak_pattern", 10, end)
    session = _session()
    try:
        dry = DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            now=end + timedelta(seconds=30),
            dry_run=True,
        )
        remaining = session.scalar(select(func.count()).select_from(AnomalyDetection)) or 0
        assert remaining == 0
        assert dry.detections_created >= 1

        first = DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            now=end + timedelta(seconds=30),
        )
        created = first.detections_created
        assert created >= 1
        numbers = list(session.scalars(select(AnomalyDetection.detection_number).order_by(AnomalyDetection.detection_number)))
        assert numbers[0] == "DET-000001"
        evidence_count = session.scalar(select(func.count()).select_from(DetectionEvidence))
        assert evidence_count and evidence_count > 0

        second = DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            now=end + timedelta(seconds=30),
        )
        assert second.detections_created == 0
        assert second.detections_deduplicated >= 1
        after = session.scalar(select(func.count()).select_from(AnomalyDetection))
        assert after == created
        incidents = session.scalar(select(func.count()).select_from(Incident))
        assert incidents == incident_count
    finally:
        session.close()


def test_recovery_then_recurrence(test_database) -> None:
    _cleanup_detections()
    first_end = _unique_end()
    _ingest_scenario("SNS-HBR-007", "pressure_drop", 10, first_end)
    session = _session()
    try:
        DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            rule_code="PRESSURE_DROP",
            now=first_end + timedelta(seconds=30),
        )
        first_count = session.scalar(select(func.count()).select_from(AnomalyDetection))
        assert first_count == 1
    finally:
        session.close()

    recovered_end = first_end + timedelta(hours=3)
    _ingest_scenario("SNS-HBR-007", "normal", 10, recovered_end)
    session = _session()
    try:
        DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            rule_code="PRESSURE_DROP",
            now=recovered_end + timedelta(seconds=30),
        )
        row = session.scalar(select(AnomalyDetection))
        assert row is not None
        assert row.evidence_summary.get("condition_open") is False
    finally:
        session.close()

    again = recovered_end + timedelta(hours=3)
    _ingest_scenario("SNS-HBR-007", "pressure_drop", 10, again)
    session = _session()
    try:
        DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            rule_code="PRESSURE_DROP",
            now=again + timedelta(seconds=30),
        )
        count = session.scalar(select(func.count()).select_from(AnomalyDetection))
        assert count == 2
    finally:
        session.close()


def test_missing_telemetry_dedup(test_database) -> None:
    _cleanup_detections()
    session = _session()
    try:
        service = TelemetryService(session)
        latest = service.repository.latest_for_sensor(service.repository.get_sensor("SNS-HBR-007").id)
        assert latest is not None
        now = latest.time + timedelta(minutes=31)
        first = DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            rule_code="MISSING_TELEMETRY",
            now=now,
        )
        second = DetectionEngine(session).run(
            sensor_external_id="SNS-HBR-007",
            rule_code="MISSING_TELEMETRY",
            now=now + timedelta(minutes=5),
        )
        assert first.detections_created == 1
        assert second.detections_created == 0
        assert second.detections_deduplicated == 1
    finally:
        session.close()


def test_flow_and_quality_and_connectivity_scenarios(test_database) -> None:
    for scenario, rule in (
        ("flow_surge", "FLOW_SURGE"),
        ("connectivity_degradation", "CONNECTIVITY_DEGRADATION"),
        ("frozen_sensor", "SENSOR_QUALITY"),
    ):
        created = 0
        last_error = ""
        for _attempt in range(4):
            _cleanup_detections()
            end = _unique_end()
            _ingest_scenario("SNS-HBR-007", scenario, 12, end)
            session = _session()
            try:
                summary = DetectionEngine(session).run(
                    sensor_external_id="SNS-HBR-007",
                    rule_code=rule,
                    now=end + timedelta(seconds=30),
                )
                created = summary.detections_created
                last_error = "; ".join(summary.error_messages)
                if created == 1:
                    break
            finally:
                session.close()
        assert created == 1, f"{scenario}: {last_error or 'no detection created'}"


def test_detection_apis(test_database, client) -> None:
    _cleanup_detections()
    end = _unique_end()
    _ingest_scenario("SNS-HBR-007", "combined_leak_pattern", 10, end)
    session = _session()
    try:
        DetectionEngine(session).run(sensor_external_id="SNS-HBR-007", now=end + timedelta(seconds=30))
    finally:
        session.close()

    listing = client.get("/api/detections")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["id"].startswith("DET-")
    number = payload["items"][0]["detection_number"]

    filtered = client.get("/api/detections", params={"sensor": "SNS-HBR-007", "priority": payload["items"][0]["priority"]})
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1

    by_rule = client.get("/api/detections", params={"rule": "COMBINED_LEAK_PATTERN"})
    assert by_rule.status_code == 200

    detail = client.get(f"/api/detections/{number}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["detection_number"] == number
    assert "score_explanation" in body
    assert body["data_mode"] == "simulated"
    assert body["incident_id"] is None

    evidence = client.get(f"/api/detections/{number}/evidence")
    assert evidence.status_code == 200
    assert len(evidence.json()["items"]) >= 1

    agent = client.get(f"/api/detections/{number}/agent-input")
    assert agent.status_code == 200
    contract = agent.json()
    assert contract["schema_version"] == "1"
    assert contract["agent_executed"] is False
    assert contract["detection_id"] == number
    assert "telemetry_window" in contract

    missing = client.get("/api/detections/DET-999999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == {"message": "Detection not found", "code": "detection_not_found"}

    summary = client.get("/api/detections/summary")
    assert summary.status_code == 200
    assert summary.json()["total"] >= 1

    mapped = client.get("/api/map/detections")
    assert mapped.status_code == 200
    assert mapped.json()["type"] == "FeatureCollection"


def test_existing_apis_unchanged(client) -> None:
    incidents = client.get("/api/incidents")
    assert incidents.status_code == 200
    assert incidents.json()["total"] == 9
    assets = client.get("/api/assets")
    assert assets.status_code == 200
    telemetry = client.get("/api/telemetry/sensors/SNS-HBR-007/latest")
    assert telemetry.status_code == 200
    zones = client.get("/api/map/zones")
    assert zones.status_code == 200


def test_seed_database_still_idempotent(test_database) -> None:
    first = seed_database()
    second = seed_database()
    assert first.detection_rules == second.detection_rules == 6
    assert first.incidents == second.incidents == 9
