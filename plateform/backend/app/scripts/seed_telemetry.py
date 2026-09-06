"""Deterministic historical sensor_readings for the 16 catalog sensors.

The most recent 24 hours keep the original 5-minute pattern. The horizon is
30 days so 7d/30d analytics have simulated history. All rows are marked
simulated. source_message_id stays deterministic and unique.
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.data.assets import get_asset_catalog
from app.data.incidents import SEED_NOW
from app.db.models import Asset, SensorReading
from app.db.session import get_session_factory
from app.services.telemetry_constants import (
    DATA_MODE,
    SENSOR_OFFLINE_END_OFFSET,
    SENSOR_SEED_HORIZON,
    SENSOR_SEED_INTERVAL,
)
from app.services.telemetry_patterns import reading_values, seed_source_id

_BATCH_SIZE = 2_000
_SEED_PAYLOAD = {"origin": "historical_seed", "data_mode": DATA_MODE}


def expected_reading_count_for_status(status: str) -> int:
    end_offset = SENSOR_OFFLINE_END_OFFSET if status == "offline" else timedelta(0)
    start = SEED_NOW - SENSOR_SEED_HORIZON
    end = SEED_NOW - end_offset
    return int((end - start) / SENSOR_SEED_INTERVAL) + 1


def expected_seed_reading_count() -> int:
    return sum(
        expected_reading_count_for_status(str(item["operational_status"]))
        for item in get_asset_catalog()
        if item["asset_type"] == "sensor"
    )


def _sync_assets_from_latest(session: Session, sensors: list[Asset]) -> None:
    for sensor in sensors:
        latest = session.scalar(
            select(SensorReading)
            .where(SensorReading.sensor_id == sensor.id)
            .order_by(SensorReading.time.desc())
            .limit(1)
        )
        if latest is None:
            continue
        sensor.last_seen_at = latest.time
        if latest.battery_pct is not None:
            sensor.battery_pct = latest.battery_pct
        if latest.signal_strength_dbm is not None:
            sensor.signal_strength_dbm = latest.signal_strength_dbm


def _flush_batch(session: Session, batch: list[dict]) -> int:
    if not batch:
        return 0
    statement = pg_insert(SensorReading).values(batch)
    statement = statement.on_conflict_do_nothing(constraint="uq_sensor_readings_sensor_time_source")
    result = session.execute(statement)
    return int(result.rowcount or 0)


def seed_sensor_readings(session: Session, *, commit: bool = True) -> int:
    sensors = list(session.scalars(select(Asset).where(Asset.asset_type == "sensor")).all())
    expected = expected_seed_reading_count()
    existing = int(
        session.scalar(
            select(func.count()).select_from(SensorReading).where(SensorReading.source_message_id.like("seed:%"))
        )
        or 0
    )
    if existing == expected:
        _sync_assets_from_latest(session, sensors)
        if commit:
            session.commit()
        else:
            session.flush()
        return 0

    inserted = 0
    batch: list[dict] = []
    for sensor in sensors:
        end = SEED_NOW
        if sensor.operational_status == "offline":
            end = SEED_NOW - SENSOR_OFFLINE_END_OFFSET
        start = SEED_NOW - SENSOR_SEED_HORIZON
        moment = start
        while moment <= end:
            values = reading_values(sensor.external_id, moment, sensor.operational_status)
            batch.append(
                {
                    "time": moment,
                    "sensor_id": sensor.id,
                    "organization_id": sensor.organization_id,
                    "source_message_id": seed_source_id(sensor.external_id, moment),
                    "pressure_kpa": values["pressure_kpa"],
                    "flow_lps": values["flow_lps"],
                    "temperature_c": values["temperature_c"],
                    "signal_strength_dbm": values["signal_strength_dbm"],
                    "packet_loss_pct": values["packet_loss_pct"],
                    "battery_pct": values["battery_pct"],
                    "quality_flags": 0,
                    "received_at": moment,
                    "raw_payload": _SEED_PAYLOAD,
                }
            )
            if len(batch) >= _BATCH_SIZE:
                inserted += _flush_batch(session, batch)
                batch = []
            moment += SENSOR_SEED_INTERVAL
    inserted += _flush_batch(session, batch)
    _sync_assets_from_latest(session, sensors)
    if commit:
        session.commit()
    else:
        session.flush()
    return inserted


def main() -> None:
    session = get_session_factory()()
    try:
        inserted = seed_sensor_readings(session)
        print(
            f"Inserted {inserted} simulated sensor readings "
            f"(expected {expected_seed_reading_count()} on a first run)."
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
