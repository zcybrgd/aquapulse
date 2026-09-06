from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AssetNotFoundError,
    DatabaseUnavailableError,
    TelemetryValidationError,
)
from app.db.models.sensor_reading import SensorReading
from app.repositories.telemetry import TelemetryRepository
from app.schemas.assets import AssetType
from app.schemas.telemetry import (
    FreshnessState,
    IngestReading,
    IngestResult,
    LatestTelemetry,
    LatestTelemetryBatch,
    MetricUnit,
    NetworkTelemetrySummary,
    SensorTelemetryHistory,
    TelemetryInterval,
    TelemetryMetric,
    TelemetryRange,
    TelemetrySample,
)
from app.services.telemetry_constants import (
    DATA_MODE,
    DEFAULT_LIMIT,
    DEFAULT_RANGE,
    FRESH_AFTER,
    INTERVAL_BUCKETS,
    MAX_QUERY_RANGE,
    MAX_RAW_POINTS,
    METRIC_COLUMNS,
    METRIC_UNITS,
    RANGE_DELTAS,
    STALE_AFTER,
)


def classify_freshness(latest: datetime | None, now: datetime) -> FreshnessState:
    if latest is None:
        return FreshnessState.offline
    age = now - latest
    if age <= FRESH_AFTER:
        return FreshnessState.fresh
    if age <= STALE_AFTER:
        return FreshnessState.stale
    return FreshnessState.offline


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TelemetryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = TelemetryRepository(session)

    def ingest(self, payload: IngestReading, *, commit: bool = True) -> IngestResult:
        try:
            sensor = self.repository.get_sensor(payload.sensor_external_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if sensor is None:
            raise AssetNotFoundError(payload.sensor_external_id)
        if sensor.asset_type != AssetType.sensor.value:
            raise TelemetryValidationError(
                "Only sensor assets accept telemetry readings.",
                code="not_a_sensor",
            )

        when = _as_utc(payload.time)
        received = _as_utc(payload.received_at or when)
        self._validate_payload(payload)

        existing = self.repository.find_by_source(sensor.id, payload.source_message_id)
        if existing is not None:
            return IngestResult(
                status="duplicate",
                sensor_id=sensor.external_id,
                time=existing.time,
                source_message_id=existing.source_message_id,
            )

        reading = SensorReading(
            time=when,
            sensor_id=sensor.id,
            organization_id=sensor.organization_id,
            source_message_id=payload.source_message_id,
            pressure_kpa=payload.pressure_kpa,
            flow_lps=payload.flow_lps,
            temperature_c=payload.temperature_c,
            signal_strength_dbm=payload.signal_strength_dbm,
            packet_loss_pct=payload.packet_loss_pct,
            battery_pct=payload.battery_pct,
            quality_flags=payload.quality_flags,
            received_at=received,
            raw_payload=payload.raw_payload or {"data_mode": DATA_MODE},
        )
        try:
            self.repository.insert(reading)
            sensor.last_seen_at = when
            if payload.battery_pct is not None:
                sensor.battery_pct = payload.battery_pct
            if payload.signal_strength_dbm is not None:
                sensor.signal_strength_dbm = payload.signal_strength_dbm
            if commit:
                self.session.commit()
        except IntegrityError:
            self.session.rollback()
            duplicate = self.repository.find_by_source(sensor.id, payload.source_message_id)
            if duplicate is None:
                raise
            return IngestResult(
                status="duplicate",
                sensor_id=sensor.external_id,
                time=duplicate.time,
                source_message_id=duplicate.source_message_id,
            )
        except (OperationalError, InterfaceError) as exc:
            self.session.rollback()
            raise DatabaseUnavailableError from exc

        return IngestResult(
            status="inserted",
            sensor_id=sensor.external_id,
            time=when,
            source_message_id=payload.source_message_id,
        )

    def history(
        self,
        sensor_id: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        range_key: str | None = None,
        interval: str = "raw",
        metrics: list[str] | None = None,
        limit: int | None = None,
    ) -> SensorTelemetryHistory:
        sensor = self._require_sensor(sensor_id)
        window_end = _as_utc(end) if end else datetime.now(timezone.utc)
        resolved_range = range_key or DEFAULT_RANGE
        if start is not None:
            window_start = _as_utc(start)
        else:
            if resolved_range not in RANGE_DELTAS:
                raise TelemetryValidationError("Unsupported telemetry range.", code="invalid_range")
            window_start = window_end - RANGE_DELTAS[resolved_range]
        if window_end - window_start > MAX_QUERY_RANGE:
            raise TelemetryValidationError(
                "Requested time range exceeds the 7-day maximum.",
                code="range_too_large",
            )
        if window_start >= window_end:
            raise TelemetryValidationError("start must be earlier than end.", code="invalid_range")
        if interval not in INTERVAL_BUCKETS:
            raise TelemetryValidationError("Unsupported aggregation interval.", code="invalid_interval")

        selected = self._parse_metrics(metrics)
        cap = min(limit or DEFAULT_LIMIT, MAX_RAW_POINTS)
        if cap < 1:
            raise TelemetryValidationError("limit must be at least 1.", code="invalid_limit")

        try:
            if interval == TelemetryInterval.raw.value:
                rows = self.repository.history_raw(
                    sensor_id=sensor.id,
                    start=window_start,
                    end=window_end,
                    limit=cap,
                    metrics=selected,
                )
                items = [self._sample_from_row(row, selected) for row in rows]
            else:
                buckets = self.repository.history_bucketed(
                    sensor_id=sensor.id,
                    start=window_start,
                    end=window_end,
                    interval=interval,
                    limit=cap,
                    metrics=selected,
                )
                items = [self._sample_from_bucket(row, selected) for row in buckets]
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc

        return SensorTelemetryHistory(
            sensor_id=sensor.external_id,
            name=sensor.name,
            range=resolved_range,
            start=window_start,
            end=window_end,
            interval=interval,
            metrics=selected,
            units=[
                MetricUnit(
                    metric=metric,
                    unit=METRIC_UNITS[metric]["unit"],
                    display_unit=METRIC_UNITS[metric]["display_unit"],
                )
                for metric in selected
            ],
            data_mode=DATA_MODE,
            items=items,
            total=len(items),
        )

    def latest(self, sensor_id: str, now: datetime | None = None) -> LatestTelemetry:
        sensor = self._require_sensor(sensor_id)
        try:
            row = self.repository.latest_for_sensor(sensor.id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        return self._latest_from_row(sensor.external_id, sensor.name, row, now)

    def latest_batch(self, now: datetime | None = None) -> LatestTelemetryBatch:
        try:
            sensors = self.repository.list_sensors()
            latest_rows = self.repository.latest_for_sensors([sensor.id for sensor in sensors])
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        items = [
            self._latest_from_row(
                sensor.external_id,
                sensor.name,
                latest_rows.get(sensor.id),
                now,
            )
            for sensor in sensors
        ]
        times = [item.time for item in items if item.time is not None]
        return LatestTelemetryBatch(
            items=items,
            total=len(items),
            data_mode=DATA_MODE,
            last_telemetry_at=max(times) if times else None,
        )

    def network_summary(self, now: datetime | None = None) -> NetworkTelemetrySummary:
        batch = self.latest_batch(now)
        clock = now or datetime.now(timezone.utc)
        _ = clock
        packet_values = [
            100.0 - item.packet_loss_pct
            for item in batch.items
            if item.packet_loss_pct is not None
        ]
        signal_values = [
            float(item.signal_strength_dbm)
            for item in batch.items
            if item.signal_strength_dbm is not None
        ]
        battery_values = [item.battery_pct for item in batch.items if item.battery_pct is not None]
        return NetworkTelemetrySummary(
            sensor_count=batch.total,
            fresh_sensors=sum(1 for item in batch.items if item.freshness == FreshnessState.fresh),
            stale_sensors=sum(1 for item in batch.items if item.freshness == FreshnessState.stale),
            offline_sensors=sum(1 for item in batch.items if item.freshness == FreshnessState.offline),
            average_packet_delivery_pct=round(sum(packet_values) / len(packet_values), 2)
            if packet_values
            else None,
            average_signal_strength_dbm=round(sum(signal_values) / len(signal_values), 1)
            if signal_values
            else None,
            average_battery_pct=round(sum(battery_values) / len(battery_values), 1)
            if battery_values
            else None,
            last_telemetry_at=batch.last_telemetry_at,
            data_mode=DATA_MODE,
        )

    def resolve_window(
        self,
        range_key: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        now: datetime | None = None,
        anchor_to_latest: bool = False,
    ) -> tuple[datetime, datetime, str]:
        resolved_range = range_key or DEFAULT_RANGE
        window_end = _as_utc(end) if end else (now or datetime.now(timezone.utc))
        if start is not None:
            window_start = _as_utc(start)
            resolved_range = range_key or "custom"
        else:
            if resolved_range not in RANGE_DELTAS:
                raise TelemetryValidationError("Unsupported telemetry range.", code="invalid_range")
            if anchor_to_latest:
                latest = self.repository.latest_time()
                if latest is not None and window_end - latest > RANGE_DELTAS[resolved_range]:
                    window_end = latest
            window_start = window_end - RANGE_DELTAS[resolved_range]
        if window_end - window_start > MAX_QUERY_RANGE:
            raise TelemetryValidationError(
                "Requested time range exceeds the 7-day maximum.",
                code="range_too_large",
            )
        if window_start >= window_end:
            raise TelemetryValidationError("start must be earlier than end.", code="invalid_range")
        return window_start, window_end, resolved_range

    def dashboard_series(self, range_key: str = "1h") -> list[TelemetrySample]:
        if range_key not in RANGE_DELTAS:
            raise TelemetryValidationError("Unsupported telemetry range.", code="invalid_range")
        start, end, _resolved = self.resolve_window(range_key, anchor_to_latest=True)
        interval = "15m" if range_key == "24h" else "5m"
        try:
            sensors = self.repository.list_sensors()
            if not sensors:
                return []
            buckets: dict[datetime, list[TelemetrySample]] = {}
            for sensor in sensors:
                rows = self.repository.history_bucketed(
                    sensor_id=sensor.id,
                    start=start,
                    end=end,
                    interval=interval,
                    limit=DEFAULT_LIMIT,
                    metrics=["pressure", "flow", "packet_loss"],
                )
                for row in rows:
                    sample = self._sample_from_bucket(row, ["pressure", "flow", "packet_loss"])
                    buckets.setdefault(sample.time, []).append(sample)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc

        merged: list[TelemetrySample] = []
        for stamp in sorted(buckets):
            group = buckets[stamp]
            merged.append(
                TelemetrySample(
                    time=stamp,
                    pressure_kpa=_avg([item.pressure_kpa for item in group]),
                    flow_lps=_avg([item.flow_lps for item in group]),
                    packet_loss_pct=_avg([item.packet_loss_pct for item in group]),
                )
            )
        return merged

    def _require_sensor(self, external_id: str):
        try:
            sensor = self.repository.get_sensor(external_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if sensor is None:
            raise AssetNotFoundError(external_id)
        if sensor.asset_type != AssetType.sensor.value:
            raise TelemetryValidationError(
                "Telemetry history is only available for sensors.",
                code="not_a_sensor",
            )
        return sensor

    def _parse_metrics(self, metrics: list[str] | None) -> list[str]:
        if not metrics:
            return list(METRIC_COLUMNS)
        invalid = [metric for metric in metrics if metric not in METRIC_COLUMNS]
        if invalid:
            raise TelemetryValidationError(
                "One or more requested metrics are not supported.",
                code="invalid_metrics",
            )
        return metrics

    def _validate_payload(self, payload: IngestReading) -> None:
        values = [
            payload.pressure_kpa,
            payload.flow_lps,
            payload.temperature_c,
            payload.signal_strength_dbm,
            payload.packet_loss_pct,
            payload.battery_pct,
        ]
        if all(value is None for value in values):
            raise TelemetryValidationError(
                "At least one measurement value is required.",
                code="no_measurements",
            )
        if payload.packet_loss_pct is not None and not 0 <= payload.packet_loss_pct <= 100:
            raise TelemetryValidationError("packet_loss_pct must be between 0 and 100.", code="invalid_percentage")
        if payload.battery_pct is not None and not 0 <= payload.battery_pct <= 100:
            raise TelemetryValidationError("battery_pct must be between 0 and 100.", code="invalid_percentage")

    def _latest_from_row(
        self,
        external_id: str,
        name: str,
        row: SensorReading | None,
        now: datetime | None,
    ) -> LatestTelemetry:
        clock = now or datetime.now(timezone.utc)
        freshness = classify_freshness(row.time if row else None, clock)
        age = int((clock - row.time).total_seconds()) if row else None
        return LatestTelemetry(
            sensor_id=external_id,
            name=name,
            time=row.time if row else None,
            pressure_kpa=row.pressure_kpa if row else None,
            flow_lps=row.flow_lps if row else None,
            temperature_c=row.temperature_c if row else None,
            signal_strength_dbm=row.signal_strength_dbm if row else None,
            packet_loss_pct=row.packet_loss_pct if row else None,
            battery_pct=row.battery_pct if row else None,
            freshness=freshness,
            age_seconds=age,
            data_mode=DATA_MODE,
        )

    def _sample_from_row(self, row: SensorReading, metrics: list[str]) -> TelemetrySample:
        payload = {"time": row.time}
        for metric in metrics:
            payload[METRIC_COLUMNS[metric]] = getattr(row, METRIC_COLUMNS[metric])
        return TelemetrySample.model_validate(payload)

    def _sample_from_bucket(self, row: dict, metrics: list[str]) -> TelemetrySample:
        payload: dict = {"time": row["bucket"]}
        for metric in metrics:
            column = METRIC_COLUMNS[metric]
            value = row.get(column)
            if column == "signal_strength_dbm" and value is not None:
                payload[column] = int(round(float(value)))
            elif value is not None:
                payload[column] = round(float(value), 3)
        return TelemetrySample.model_validate(payload)


def _avg(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 3)
