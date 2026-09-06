from app.scripts.simulate_telemetry import main, simulate_once
from app.db.session import get_session_factory
from uuid import uuid4

from sqlalchemy import func, select

from app.db.models import SensorReading


def test_simulator_disabled_by_default(test_database) -> None:
    assert main([]) == 2


def test_simulator_once_and_specific_sensor(test_database, capsys) -> None:
    session = get_session_factory()()
    try:
        before = session.scalar(
            select(func.count())
            .select_from(SensorReading)
            .where(SensorReading.source_message_id.like("sim:SNS-HBR-007:%"))
        ) or 0
    finally:
        session.close()

    assert main(["--once", "--enable", "--sensor", "SNS-HBR-007"]) == 0
    output = capsys.readouterr().out
    assert "SNS-HBR-007" in output
    assert "cycle 1" in output

    session = get_session_factory()()
    try:
        after = session.scalar(
            select(func.count())
            .select_from(SensorReading)
            .where(SensorReading.source_message_id.like("sim:SNS-HBR-007:%"))
        ) or 0
    finally:
        session.close()
    assert after == before + 1


def test_simulator_skips_offline_sensor(test_database) -> None:
    lines = simulate_once(sensor_id="SNS-AIN-220")
    assert lines == ["skip SNS-AIN-220 (offline)"]


def test_simulator_duplicate_source_is_handled(test_database) -> None:
    from datetime import datetime, timedelta, timezone

    from app.schemas.telemetry import IngestReading
    from app.services.telemetry import TelemetryService
    from app.services.telemetry_patterns import reading_values

    session = get_session_factory()()
    try:
        service = TelemetryService(session)
        when = datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=uuid4().int % 10_000_000)
        payload = IngestReading(
            sensor_external_id="SNS-CRN-014",
            time=when,
            source_message_id=f"sim:SNS-CRN-014:dup-test-{uuid4()}",
            received_at=when,
            **reading_values("SNS-CRN-014", when, "online"),
        )
        first = service.ingest(payload)
        second = service.ingest(payload)
        assert first.status == "inserted"
        assert second.status == "duplicate"
    finally:
        session.close()
