from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AnalyticsValidationError, AssetNotFoundError, ZoneNotFoundError
from app.db.models import Incident
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsAssetsResponse,
    AnalyticsDetectionsResponse,
    AnalyticsEnvelope,
    AnalyticsFilters,
    AnalyticsIncidentsResponse,
    AnalyticsOperationsResponse,
    AnalyticsOverviewResponse,
    AnalyticsTelemetryResponse,
    AnalyticsZonesResponse,
    AssetHealthBucket,
    ComparedMetric,
    NamedCount,
    TimeSeriesPoint,
    ZoneAnalyticsRow,
)
from app.services.analytics_constants import (
    ALLOWED_INTERVALS_FOR_RANGE,
    ANALYTICS_DATA_MODE,
    ANALYTICS_NOW,
    INSUFFICIENT_ZONE_READINGS,
    INTERVAL_DELTAS,
    RANGE_DELTAS,
    SAMPLE_INTERVAL,
    compare_values,
    default_interval,
    iter_buckets,
    resolve_windows,
)
from app.services.telemetry import classify_freshness
from app.services.telemetry_constants import SENSOR_OFFLINE_END_OFFSET

SEVERITY_LABELS = {1: "tier_1", 2: "tier_2", 3: "tier_3"}
HEALTH_LABELS = {
    "healthy": "Healthy",
    "fair": "Fair",
    "poor": "Poor",
    "unknown": "Unknown",
}


class AnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AnalyticsRepository(session)

    def overview(self, range_key: str, *, zone: str | None = None, sensor: str | None = None) -> AnalyticsOverviewResponse:
        start, end, prev_start, prev_end = self._window(range_key)
        self._validate_scope(zone, sensor)
        sensors = self.repository.list_sensors(zone=zone, sensor=sensor)
        current = self.repository.telemetry_summary(start=start, end=end, zone=zone, sensor=sensor)
        previous = self.repository.telemetry_summary(
            start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        current_complete = self._completeness(current["reading_count"], sensors, start, end)
        previous_complete = self._completeness(previous["reading_count"], sensors, prev_start, prev_end, inclusive_end=False)
        current_events = self.repository.incident_counts(start=start, end=end, zone=zone, sensor=sensor)
        previous_events = self.repository.incident_counts(
            start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        current_active = self.repository.active_incident_count(as_of=end, zone=zone, sensor=sensor)
        previous_active = self.repository.active_incident_count(as_of=prev_end, zone=zone, sensor=sensor)
        current_response = self.repository.duration_stats(
            Incident.detected_at, Incident.response_started_at, start=start, end=end, zone=zone, sensor=sensor
        )
        previous_response = self.repository.duration_stats(
            Incident.detected_at,
            Incident.response_started_at,
            start=prev_start,
            end=prev_end,
            zone=zone,
            sensor=sensor,
            inclusive_end=False,
        )
        detection_current = self.repository.detection_counts(start=start, end=end, zone=zone, sensor=sensor)
        detection_previous = self.repository.detection_counts(
            start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        ops_current = self.repository.task_counts(start=start, end=end, as_of=end, zone=zone, sensor=sensor)
        ops_previous = self.repository.task_counts(
            start=prev_start, end=prev_end, as_of=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        ack = self.repository.duration_stats(
            Incident.detected_at, Incident.acknowledged_at, start=start, end=end, zone=zone, sensor=sensor
        )
        ack_prev = self.repository.duration_stats(
            Incident.detected_at,
            Incident.acknowledged_at,
            start=prev_start,
            end=prev_end,
            zone=zone,
            sensor=sensor,
            inclusive_end=False,
        )
        resolved = self.repository.duration_stats(
            Incident.detected_at, Incident.resolved_at, start=start, end=end, zone=zone, sensor=sensor
        )
        resolved_prev = self.repository.duration_stats(
            Incident.detected_at,
            Incident.resolved_at,
            start=prev_start,
            end=prev_end,
            zone=zone,
            sensor=sensor,
            inclusive_end=False,
        )

        kpis = [
            self._metric("average_pressure", "Average pressure", "bar", current["avg_pressure_bar"], previous["avg_pressure_bar"], "neutral"),
            self._metric("average_flow", "Average flow", "m³/h", current["avg_flow_m3h"], previous["avg_flow_m3h"], "neutral"),
            self._metric(
                "estimated_monitored_volume",
                "Estimated monitored volume",
                "m³",
                current["estimated_monitored_volume_m3"],
                previous["estimated_monitored_volume_m3"],
                "neutral",
            ),
            self._metric("telemetry_completeness", "Telemetry completeness", "%", current_complete, previous_complete, "higher_is_better"),
            self._metric("active_incidents", "Active incidents", None, float(current_active), float(previous_active), "neutral"),
            self._metric(
                "mean_response_time",
                "Mean response time",
                "min",
                current_response["mean_minutes"],
                previous_response["mean_minutes"],
                "lower_is_better",
            ),
        ]
        envelope = self._envelope(range_key, start, end, zone, sensor)
        return AnalyticsOverviewResponse(
            **envelope,
            kpis=kpis,
            telemetry={
                "average_pressure": kpis[0],
                "average_flow": kpis[1],
                "estimated_monitored_volume": kpis[2],
                "telemetry_completeness": kpis[3],
                "packet_loss": self._metric(
                    "packet_loss",
                    "Average packet loss",
                    "%",
                    current["avg_packet_loss_pct"],
                    previous["avg_packet_loss_pct"],
                    "lower_is_better",
                ),
            },
            events={
                "detections_created": self._metric(
                    "detections_created",
                    "Detections created",
                    None,
                    float(detection_current["created"]),
                    float(detection_previous["created"]),
                    "neutral",
                ),
                "incidents_created": self._metric(
                    "incidents_created",
                    "Incidents created",
                    None,
                    float(current_events["created"]),
                    float(previous_events["created"]),
                    "neutral",
                ),
            },
            operations={
                "mean_acknowledgement": self._metric(
                    "mean_acknowledgement",
                    "Mean acknowledgement time",
                    "min",
                    ack["mean_minutes"],
                    ack_prev["mean_minutes"],
                    "lower_is_better",
                ),
                "mean_resolution": self._metric(
                    "mean_resolution",
                    "Mean resolution time",
                    "min",
                    resolved["mean_minutes"],
                    resolved_prev["mean_minutes"],
                    "lower_is_better",
                ),
                "overdue_response_tasks": self._metric(
                    "overdue_response_tasks",
                    "Overdue response tasks",
                    None,
                    float(ops_current["overdue_response_tasks"]),
                    float(ops_previous["overdue_response_tasks"]),
                    "lower_is_better",
                ),
            },
            available_zones=self.repository.list_zone_names(),
            available_sensors=self.repository.list_sensor_ids(zone=zone),
        )

    def telemetry(
        self,
        range_key: str,
        *,
        zone: str | None = None,
        sensor: str | None = None,
        interval: str | None = None,
    ) -> AnalyticsTelemetryResponse:
        start, end, prev_start, prev_end = self._window(range_key)
        interval_key = self._interval(range_key, interval)
        self._validate_scope(zone, sensor)
        sensors = self.repository.list_sensors(zone=zone, sensor=sensor)
        current = self.repository.telemetry_summary(start=start, end=end, zone=zone, sensor=sensor)
        previous = self.repository.telemetry_summary(
            start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        completeness = self._completeness(current["reading_count"], sensors, start, end)
        prev_completeness = self._completeness(
            previous["reading_count"], sensors, prev_start, prev_end, inclusive_end=False
        )
        series_rows = self.repository.telemetry_series(
            start=start,
            end=end,
            interval=interval_key,
            zone=zone,
            sensor=sensor,
            selected_sensors=len(sensors),
        )
        series_map = {row["timestamp"]: row for row in series_rows}
        series = []
        for bucket in iter_buckets(start, end, INTERVAL_DELTAS[interval_key]):
            row = series_map.get(bucket)
            if row is None:
                series.append(TimeSeriesPoint(timestamp=bucket))
                continue
            series.append(TimeSeriesPoint(**row))
        freshness = self._freshness(sensors)
        envelope = self._envelope(range_key, start, end, zone, sensor, interval_key)
        return AnalyticsTelemetryResponse(
            **envelope,
            interval=interval_key,
            summary={
                "average_pressure": self._metric("average_pressure", "Average pressure", "bar", current["avg_pressure_bar"], previous["avg_pressure_bar"], "neutral"),
                "minimum_pressure": self._metric("minimum_pressure", "Minimum pressure", "bar", current["min_pressure_bar"], previous["min_pressure_bar"], "neutral"),
                "maximum_pressure": self._metric("maximum_pressure", "Maximum pressure", "bar", current["max_pressure_bar"], previous["max_pressure_bar"], "neutral"),
                "average_flow": self._metric("average_flow", "Average flow", "m³/h", current["avg_flow_m3h"], previous["avg_flow_m3h"], "neutral"),
                "estimated_monitored_volume": self._metric(
                    "estimated_monitored_volume",
                    "Estimated monitored volume",
                    "m³",
                    current["estimated_monitored_volume_m3"],
                    previous["estimated_monitored_volume_m3"],
                    "neutral",
                ),
                "average_packet_loss": self._metric(
                    "average_packet_loss",
                    "Average packet loss",
                    "%",
                    current["avg_packet_loss_pct"],
                    previous["avg_packet_loss_pct"],
                    "lower_is_better",
                ),
                "average_signal": self._metric("average_signal", "Average signal strength", "dBm", current["avg_signal_dbm"], previous["avg_signal_dbm"], "higher_is_better"),
                "average_battery": self._metric("average_battery", "Average battery", "%", current["avg_battery_pct"], previous["avg_battery_pct"], "higher_is_better"),
                "telemetry_completeness": self._metric(
                    "telemetry_completeness",
                    "Telemetry completeness",
                    "%",
                    completeness,
                    prev_completeness,
                    "higher_is_better",
                ),
            },
            series=series,
            reporting_sensors=current["reporting_sensors"],
            stale_sensors=freshness["stale"],
            offline_sensors=freshness["offline"],
            selected_sensors=len(sensors),
        )

    def zones(self, range_key: str, *, zone: str | None = None) -> AnalyticsZonesResponse:
        start, end, _, _ = self._window(range_key)
        self._validate_scope(zone, None)
        items = [
            ZoneAnalyticsRow(**row)
            for row in self.repository.zone_rows(start=start, end=end, as_of=end, zone=zone)
        ]
        for item in items:
            if item.reporting_sensors < INSUFFICIENT_ZONE_READINGS:
                item.sufficient_data = False
                item.average_pressure_bar = None
                item.average_flow_m3h = None
                item.telemetry_completeness_pct = None
        envelope = self._envelope(range_key, start, end, zone, None)
        return AnalyticsZonesResponse(**envelope, items=items)

    def detections(
        self,
        range_key: str,
        *,
        zone: str | None = None,
        sensor: str | None = None,
        interval: str | None = None,
    ) -> AnalyticsDetectionsResponse:
        start, end, prev_start, prev_end = self._window(range_key)
        interval_key = self._interval(range_key, interval)
        self._validate_scope(zone, sensor)
        current = self.repository.detection_counts(start=start, end=end, zone=zone, sensor=sensor)
        previous = self.repository.detection_counts(
            start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        current_rate = _rate(current["promoted"], current["created"])
        previous_rate = _rate(previous["promoted"], previous["created"])
        series_map = {
            row["timestamp"]: row["detections"]
            for row in self.repository.detection_series(
                start=start, end=end, interval=interval_key, zone=zone, sensor=sensor
            )
        }
        series = [
            TimeSeriesPoint(timestamp=bucket, detections=series_map.get(bucket))
            for bucket in iter_buckets(start, end, INTERVAL_DELTAS[interval_key])
        ]
        envelope = self._envelope(range_key, start, end, zone, sensor, interval_key)
        return AnalyticsDetectionsResponse(
            **envelope,
            interval=interval_key,
            created=self._metric("detections_created", "Detections created", None, float(current["created"]), float(previous["created"]), "neutral"),
            dismissed=self._metric("detections_dismissed", "Dismissed detections", None, float(current["dismissed"]), float(previous["dismissed"]), "neutral"),
            promoted=self._metric("detections_promoted", "Promoted detections", None, float(current["promoted"]), float(previous["promoted"]), "neutral"),
            promotion_rate=self._metric("promotion_rate", "Promotion rate", "%", current_rate, previous_rate, "neutral"),
            by_priority=[NamedCount(key=key, label=key.replace("_", " ").title(), count=count) for key, count in self.repository.detections_by_priority(start=start, end=end, zone=zone, sensor=sensor)],
            by_rule=[
                NamedCount(key=code, label=name, count=count)
                for code, name, count in self.repository.detections_by_rule(start=start, end=end, zone=zone, sensor=sensor)
            ],
            series=series,
        )

    def incidents(
        self,
        range_key: str,
        *,
        zone: str | None = None,
        sensor: str | None = None,
        interval: str | None = None,
    ) -> AnalyticsIncidentsResponse:
        start, end, prev_start, prev_end = self._window(range_key)
        interval_key = self._interval(range_key, interval)
        self._validate_scope(zone, sensor)
        current = self.repository.incident_counts(start=start, end=end, zone=zone, sensor=sensor)
        previous = self.repository.incident_counts(
            start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        series_map = {
            row["timestamp"]: row["incidents"]
            for row in self.repository.incident_series(start=start, end=end, interval=interval_key, zone=zone, sensor=sensor)
        }
        series = [
            TimeSeriesPoint(timestamp=bucket, incidents=series_map.get(bucket))
            for bucket in iter_buckets(start, end, INTERVAL_DELTAS[interval_key])
        ]
        envelope = self._envelope(range_key, start, end, zone, sensor, interval_key)
        return AnalyticsIncidentsResponse(
            **envelope,
            interval=interval_key,
            created=self._metric("incidents_created", "Incidents created", None, float(current["created"]), float(previous["created"]), "neutral"),
            resolved=self._metric("incidents_resolved", "Incidents resolved", None, float(current["resolved"]), float(previous["resolved"]), "neutral"),
            false_alarms=self._metric("false_alarms", "False alarms", None, float(current["false_alarms"]), float(previous["false_alarms"]), "neutral"),
            by_severity=[
                NamedCount(key=SEVERITY_LABELS.get(int(key), str(key)), label=SEVERITY_LABELS.get(int(key), str(key)).replace("_", " ").title(), count=count)
                for key, count in self.repository.incidents_grouped(
                    Incident.severity_tier, start=start, end=end, zone=zone, sensor=sensor
                )
            ],
            by_classification=[
                NamedCount(key=key, label=key.replace("_", " ").title(), count=count)
                for key, count in self.repository.incidents_grouped(
                    Incident.classification, start=start, end=end, zone=zone, sensor=sensor
                )
            ],
            by_status=[
                NamedCount(key=key, label=key.replace("_", " ").title(), count=count)
                for key, count in self.repository.incidents_grouped(
                    Incident.status, start=start, end=end, zone=zone, sensor=sensor
                )
            ],
            series=series,
        )

    def operations(
        self,
        range_key: str,
        *,
        zone: str | None = None,
        sensor: str | None = None,
        interval: str | None = None,
    ) -> AnalyticsOperationsResponse:
        start, end, prev_start, prev_end = self._window(range_key)
        interval_key = self._interval(range_key, interval)
        self._validate_scope(zone, sensor)
        ack = self.repository.duration_stats(Incident.detected_at, Incident.acknowledged_at, start=start, end=end, zone=zone, sensor=sensor)
        ack_prev = self.repository.duration_stats(
            Incident.detected_at, Incident.acknowledged_at, start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        response = self.repository.duration_stats(Incident.detected_at, Incident.response_started_at, start=start, end=end, zone=zone, sensor=sensor)
        response_prev = self.repository.duration_stats(
            Incident.detected_at, Incident.response_started_at, start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        resolved = self.repository.duration_stats(Incident.detected_at, Incident.resolved_at, start=start, end=end, zone=zone, sensor=sensor)
        resolved_prev = self.repository.duration_stats(
            Incident.detected_at, Incident.resolved_at, start=prev_start, end=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        tasks = self.repository.task_counts(start=start, end=end, as_of=end, zone=zone, sensor=sensor)
        tasks_prev = self.repository.task_counts(
            start=prev_start, end=prev_end, as_of=prev_end, zone=zone, sensor=sensor, inclusive_end=False
        )
        series_map = {
            row["timestamp"]: row["mean_response_minutes"]
            for row in self.repository.response_series(start=start, end=end, interval=interval_key, zone=zone, sensor=sensor)
        }
        series = [
            TimeSeriesPoint(timestamp=bucket, mean_response_minutes=series_map.get(bucket))
            for bucket in iter_buckets(start, end, INTERVAL_DELTAS[interval_key])
        ]
        envelope = self._envelope(range_key, start, end, zone, sensor, interval_key)
        return AnalyticsOperationsResponse(
            **envelope,
            interval=interval_key,
            mean_acknowledgement_minutes=self._metric("mean_acknowledgement", "Mean acknowledgement time", "min", ack["mean_minutes"], ack_prev["mean_minutes"], "lower_is_better"),
            median_acknowledgement_minutes=self._metric("median_acknowledgement", "Median acknowledgement time", "min", ack["median_minutes"], ack_prev["median_minutes"], "lower_is_better"),
            mean_response_start_minutes=self._metric("mean_response_start", "Mean response-start time", "min", response["mean_minutes"], response_prev["mean_minutes"], "lower_is_better"),
            mean_resolution_minutes=self._metric("mean_resolution", "Mean resolution time", "min", resolved["mean_minutes"], resolved_prev["mean_minutes"], "lower_is_better"),
            open_response_tasks=self._metric("open_response_tasks", "Open response tasks", None, float(tasks["open_response_tasks"]), float(tasks_prev["open_response_tasks"]), "neutral"),
            completed_response_tasks=self._metric("completed_response_tasks", "Completed response tasks", None, float(tasks["completed_response_tasks"]), float(tasks_prev["completed_response_tasks"]), "neutral"),
            overdue_response_tasks=self._metric("overdue_response_tasks", "Overdue response tasks", None, float(tasks["overdue_response_tasks"]), float(tasks_prev["overdue_response_tasks"]), "lower_is_better"),
            series=series,
        )

    def assets(self, range_key: str, *, zone: str | None = None, sensor: str | None = None) -> AnalyticsAssetsResponse:
        start, end, _, _ = self._window(range_key)
        self._validate_scope(zone, sensor)
        distribution = self.repository.asset_health_distribution(zone=zone, sensor=sensor)
        bands = {"healthy": 0, "fair": 0, "poor": 0, "unknown": 0}
        scores: list[float] = []
        statuses: dict[str, int] = {}
        types = distribution["types"]
        for score in distribution["health_scores"]:
            if score is None:
                bands["unknown"] += 1
                continue
            scores.append(float(score))
            if score >= 80:
                bands["healthy"] += 1
            elif score >= 60:
                bands["fair"] += 1
            else:
                bands["poor"] += 1
        for status in distribution["statuses"]:
            statuses[status] = statuses.get(status, 0) + 1
        sensors = self.repository.list_sensors(zone=zone, sensor=sensor)
        freshness = self._freshness(sensors)
        envelope = self._envelope(range_key, start, end, zone, sensor)
        return AnalyticsAssetsResponse(
            **envelope,
            health_bands=[AssetHealthBucket(key=key, label=HEALTH_LABELS[key], count=count) for key, count in bands.items()],
            operational_status=[NamedCount(key=key, label=key.title(), count=count) for key, count in sorted(statuses.items())],
            connectivity=[
                NamedCount(key="fresh", label="Fresh", count=freshness["fresh"]),
                NamedCount(key="stale", label="Stale", count=freshness["stale"]),
                NamedCount(key="offline", label="Offline", count=freshness["offline"]),
            ],
            average_health=round(sum(scores) / len(scores), 1) if scores else None,
            sensor_count=sum(1 for item in types if item == "sensor"),
            total_assets=len(types),
        )

    def _window(self, range_key: str) -> tuple[datetime, datetime, datetime, datetime]:
        if range_key not in RANGE_DELTAS:
            raise AnalyticsValidationError("Range must be 24h, 7d or 30d.", code="invalid_analytics_range")
        return resolve_windows(range_key)

    def _interval(self, range_key: str, interval: str | None) -> str:
        key = interval or default_interval(range_key)
        if key not in INTERVAL_DELTAS or key not in ALLOWED_INTERVALS_FOR_RANGE[range_key]:
            raise AnalyticsValidationError(
                f"Interval {key} is not valid for range {range_key}.",
                code="invalid_analytics_interval",
            )
        return key

    def _validate_scope(self, zone: str | None, sensor: str | None) -> None:
        if zone:
            if self.repository.get_zone_by_name(zone) is None:
                raise ZoneNotFoundError(zone)
        if sensor:
            match = self.repository.list_sensors(sensor=sensor)
            if not match:
                raise AssetNotFoundError(sensor)

    def _envelope(
        self,
        range_key: str,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        interval: str | None = None,
    ) -> dict:
        _ = AnalyticsEnvelope
        return {
            "range": range_key,
            "start": start,
            "end": end,
            "generated_at": datetime.now(timezone.utc),
            "data_mode": ANALYTICS_DATA_MODE,
            "filters": AnalyticsFilters(zone=zone, sensor=sensor, interval=interval),
        }

    def _metric(
        self,
        key: str,
        label: str,
        unit: str | None,
        current: float | None,
        previous: float | None,
        interpretation: str,
    ) -> ComparedMetric:
        change, change_pct, trend = compare_values(current, previous)
        return ComparedMetric(
            key=key,
            label=label,
            unit=unit,
            current=current,
            previous=previous,
            change=None if change is None else round(change, 3),
            change_pct=None if change_pct is None else round(change_pct, 1),
            trend=trend,
            interpretation=interpretation,  # type: ignore[arg-type]
        )

    def _completeness(
        self,
        reading_count: int,
        sensors: list,
        start: datetime,
        end: datetime,
        *,
        inclusive_end: bool = True,
    ) -> float | None:
        expected = 0
        for sensor in sensors:
            sensor_end = end
            if sensor.operational_status == "offline":
                sensor_end = min(end, ANALYTICS_NOW - SENSOR_OFFLINE_END_OFFSET)
            if sensor_end < start:
                continue
            if inclusive_end:
                expected += int((sensor_end - start) / SAMPLE_INTERVAL) + 1
            else:
                span = sensor_end - start
                if span.total_seconds() <= 0:
                    continue
                expected += max(0, int(span / SAMPLE_INTERVAL))
        if expected <= 0:
            return None
        return round(min(100.0, (reading_count / expected) * 100.0), 1)

    def _freshness(self, sensors: list) -> dict[str, int]:
        latest = self.repository.latest_reading_times([sensor.id for sensor in sensors])
        counts = {"fresh": 0, "stale": 0, "offline": 0}
        for sensor in sensors:
            state = classify_freshness(latest.get(sensor.id), ANALYTICS_NOW)
            counts[state] += 1
        return counts


def _rate(part: int, whole: int) -> float | None:
    if whole <= 0:
        return None
    return round((part / whole) * 100.0, 1)
