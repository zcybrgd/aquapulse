from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.orm import Session

from app.db.models import Asset, SensorReading
from app.services.telemetry_constants import INTERVAL_BUCKETS, METRIC_COLUMNS


class TelemetryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_sensor(self, external_id: str) -> Asset | None:
        return self.session.scalar(select(Asset).where(Asset.external_id == external_id))

    def list_sensors(self) -> list[Asset]:
        return list(
            self.session.scalars(
                select(Asset).where(Asset.asset_type == "sensor").order_by(Asset.external_id)
            ).all()
        )

    def find_by_source(self, sensor_id: UUID, source_message_id: str) -> SensorReading | None:
        return self.session.scalar(
            select(SensorReading).where(
                SensorReading.sensor_id == sensor_id,
                SensorReading.source_message_id == source_message_id,
            )
        )

    def insert(self, reading: SensorReading) -> None:
        self.session.add(reading)

    def latest_for_sensor(self, sensor_id: UUID) -> SensorReading | None:
        return self.session.scalar(
            select(SensorReading)
            .where(SensorReading.sensor_id == sensor_id)
            .order_by(SensorReading.time.desc())
            .limit(1)
        )

    def has_readings(self, sensor_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(SensorReading.sensor_id).where(SensorReading.sensor_id == sensor_id).limit(1)
            )
            is not None
        )

    def latest_for_sensors(self, sensor_ids: list[UUID]) -> dict[UUID, SensorReading]:
        if not sensor_ids:
            return {}
        rows = self.session.scalars(
            select(SensorReading)
            .where(SensorReading.sensor_id.in_(sensor_ids))
            .distinct(SensorReading.sensor_id)
            .order_by(SensorReading.sensor_id, SensorReading.time.desc())
        )
        return {row.sensor_id: row for row in rows}

    def history_raw(
        self,
        *,
        sensor_id: UUID,
        start: datetime,
        end: datetime,
        limit: int,
        metrics: list[str],
    ) -> list[SensorReading]:
        columns = [getattr(SensorReading, METRIC_COLUMNS[metric]) for metric in metrics]
        stmt: Select = (
            select(SensorReading)
            .where(
                SensorReading.sensor_id == sensor_id,
                SensorReading.time >= start,
                SensorReading.time <= end,
            )
            .order_by(SensorReading.time.asc())
            .limit(limit)
        )
        _ = columns
        return list(self.session.scalars(stmt).all())

    def history_bucketed(
        self,
        *,
        sensor_id: UUID,
        start: datetime,
        end: datetime,
        interval: str,
        limit: int,
        metrics: list[str],
    ) -> list[dict]:
        delta = INTERVAL_BUCKETS[interval]
        assert delta is not None
        bucket = func.time_bucket(
            literal_column(f"INTERVAL '{int(delta.total_seconds())} seconds'"),
            SensorReading.time,
        ).label("bucket")
        aggregates = [bucket]
        for metric in metrics:
            column = getattr(SensorReading, METRIC_COLUMNS[metric])
            aggregates.append(func.avg(column).label(METRIC_COLUMNS[metric]))
        stmt = (
            select(*aggregates)
            .where(
                SensorReading.sensor_id == sensor_id,
                SensorReading.time >= start,
                SensorReading.time <= end,
            )
            .group_by(bucket)
            .order_by(bucket.asc())
            .limit(limit)
        )
        return [dict(row._mapping) for row in self.session.execute(stmt)]

    def count_for_sensor(self, sensor_id: UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(SensorReading).where(SensorReading.sensor_id == sensor_id)
            )
            or 0
        )

    def count_all(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(SensorReading)) or 0)

    def latest_time(self) -> datetime | None:
        return self.session.scalar(select(func.max(SensorReading.time)))
