from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.orm import Session, aliased

from app.db.models import (
    AnomalyDetection,
    Asset,
    DetectionRule,
    Incident,
    IncidentResponseTask,
    SensorReading,
    Zone,
)
from app.incident.workflow import OPEN_TASK_STATUSES
from app.services.analytics_constants import INTERVAL_DELTAS, SAMPLE_INTERVAL_SECONDS
from app.services.telemetry_constants import KPA_TO_BAR, LPS_TO_M3H


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_zone_by_name(self, name: str) -> Zone | None:
        return self.session.scalar(select(Zone).where(func.lower(Zone.name) == name.strip().casefold()))

    def list_zone_names(self) -> list[str]:
        rows = self.session.scalars(select(Zone.name).order_by(Zone.name.asc()))
        return list(rows)

    def list_sensor_ids(self, *, zone: str | None = None) -> list[str]:
        stmt = select(Asset.external_id).where(Asset.asset_type == "sensor")
        if zone:
            stmt = stmt.join(Zone, Asset.zone_id == Zone.id).where(func.lower(Zone.name) == zone.strip().casefold())
        return list(self.session.scalars(stmt.order_by(Asset.external_id.asc())))

    def list_sensors(self, *, zone: str | None = None, sensor: str | None = None) -> list[Asset]:
        stmt = select(Asset).where(Asset.asset_type == "sensor")
        if zone:
            stmt = stmt.join(Zone, Asset.zone_id == Zone.id).where(func.lower(Zone.name) == zone.strip().casefold())
        if sensor:
            stmt = stmt.where(Asset.external_id == sensor)
        return list(self.session.scalars(stmt.order_by(Asset.external_id.asc())).unique().all())

    def _reading_stmt(
        self,
        *columns,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool = True,
    ) -> Select:
        stmt = select(*columns).select_from(SensorReading).join(Asset, SensorReading.sensor_id == Asset.id)
        if zone:
            stmt = stmt.join(Zone, Asset.zone_id == Zone.id)
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if sensor:
            stmt = stmt.where(Asset.external_id == sensor)
        if inclusive_end:
            stmt = stmt.where(SensorReading.time >= start, SensorReading.time <= end)
        else:
            stmt = stmt.where(SensorReading.time >= start, SensorReading.time < end)
        return stmt

    def telemetry_summary(
        self,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool = True,
    ) -> dict:
        volume_expr = func.sum(SensorReading.flow_lps) * SAMPLE_INTERVAL_SECONDS / 1000.0
        stmt = self._reading_stmt(
            func.avg(SensorReading.pressure_kpa).label("avg_pressure_kpa"),
            func.min(SensorReading.pressure_kpa).label("min_pressure_kpa"),
            func.max(SensorReading.pressure_kpa).label("max_pressure_kpa"),
            func.avg(SensorReading.flow_lps).label("avg_flow_lps"),
            volume_expr.label("volume_m3"),
            func.avg(SensorReading.packet_loss_pct).label("avg_packet_loss"),
            func.avg(SensorReading.signal_strength_dbm).label("avg_signal"),
            func.avg(SensorReading.battery_pct).label("avg_battery"),
            func.count().label("reading_count"),
            func.count(func.distinct(SensorReading.sensor_id)).label("reporting_sensors"),
            start=start,
            end=end,
            zone=zone,
            sensor=sensor,
            inclusive_end=inclusive_end,
        )
        row = self.session.execute(stmt).one()
        mapping = dict(row._mapping)
        return {
            "avg_pressure_bar": _scale(mapping["avg_pressure_kpa"], KPA_TO_BAR, 3),
            "min_pressure_bar": _scale(mapping["min_pressure_kpa"], KPA_TO_BAR, 3),
            "max_pressure_bar": _scale(mapping["max_pressure_kpa"], KPA_TO_BAR, 3),
            "avg_flow_m3h": _scale(mapping["avg_flow_lps"], LPS_TO_M3H, 2),
            "estimated_monitored_volume_m3": _round(mapping["volume_m3"], 1),
            "avg_packet_loss_pct": _round(mapping["avg_packet_loss"], 2),
            "avg_signal_dbm": _round(mapping["avg_signal"], 1),
            "avg_battery_pct": _round(mapping["avg_battery"], 1),
            "reading_count": int(mapping["reading_count"] or 0),
            "reporting_sensors": int(mapping["reporting_sensors"] or 0),
        }

    def telemetry_series(
        self,
        *,
        start: datetime,
        end: datetime,
        interval: str,
        zone: str | None,
        sensor: str | None,
        selected_sensors: int,
    ) -> list[dict]:
        delta = INTERVAL_DELTAS[interval]
        bucket = func.time_bucket(
            literal_column(f"INTERVAL '{int(delta.total_seconds())} seconds'"),
            SensorReading.time,
        ).label("bucket")
        expected = selected_sensors * (delta.total_seconds() / SAMPLE_INTERVAL_SECONDS)
        completeness = (
            literal_column("NULL")
            if expected <= 0
            else func.count() * 100.0 / expected
        )
        stmt = self._reading_stmt(
            bucket,
            func.avg(SensorReading.pressure_kpa).label("avg_pressure_kpa"),
            func.avg(SensorReading.flow_lps).label("avg_flow_lps"),
            func.avg(SensorReading.packet_loss_pct).label("avg_packet_loss"),
            completeness.label("completeness_pct"),
            func.count(func.distinct(SensorReading.sensor_id)).label("reporting_sensors"),
            func.count().label("reading_count"),
            start=start,
            end=end,
            zone=zone,
            sensor=sensor,
        ).group_by(bucket).order_by(bucket.asc())
        rows = []
        for row in self.session.execute(stmt):
            mapping = dict(row._mapping)
            rows.append(
                {
                    "timestamp": mapping["bucket"],
                    "pressure_bar": _scale(mapping["avg_pressure_kpa"], KPA_TO_BAR, 3),
                    "flow_m3h": _scale(mapping["avg_flow_lps"], LPS_TO_M3H, 2),
                    "packet_loss_pct": _round(mapping["avg_packet_loss"], 2),
                    "completeness_pct": _round(mapping["completeness_pct"], 1),
                    "reporting_sensors": int(mapping["reporting_sensors"] or 0),
                    "reading_count": int(mapping["reading_count"] or 0),
                }
            )
        return rows

    def detection_counts(
        self,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool = True,
    ) -> dict[str, int]:
        stmt = select(
            func.count().label("created"),
            func.count().filter(AnomalyDetection.status == "dismissed").label("dismissed"),
            func.count().filter(AnomalyDetection.status == "promoted").label("promoted"),
        ).select_from(AnomalyDetection)
        stmt = self._detection_filters(stmt, start, end, zone, sensor, inclusive_end)
        row = self.session.execute(stmt).one()
        return {key: int(value or 0) for key, value in dict(row._mapping).items()}

    def detections_by_priority(
        self,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
    ) -> list[tuple[str, int]]:
        stmt = select(AnomalyDetection.priority, func.count()).select_from(AnomalyDetection)
        stmt = self._detection_filters(stmt, start, end, zone, sensor, True)
        stmt = stmt.group_by(AnomalyDetection.priority).order_by(AnomalyDetection.priority)
        return [(str(key), int(count)) for key, count in self.session.execute(stmt)]

    def detections_by_rule(
        self,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
    ) -> list[tuple[str, str, int]]:
        stmt = (
            select(DetectionRule.code, DetectionRule.name, func.count())
            .select_from(AnomalyDetection)
            .join(DetectionRule, AnomalyDetection.rule_id == DetectionRule.id)
        )
        stmt = self._detection_filters(stmt, start, end, zone, sensor, True, already_from_detection=True)
        stmt = stmt.group_by(DetectionRule.code, DetectionRule.name).order_by(DetectionRule.code)
        return [(str(code), str(name), int(count)) for code, name, count in self.session.execute(stmt)]

    def detection_series(
        self,
        *,
        start: datetime,
        end: datetime,
        interval: str,
        zone: str | None,
        sensor: str | None,
    ) -> list[dict]:
        delta = INTERVAL_DELTAS[interval]
        bucket = func.time_bucket(
            literal_column(f"INTERVAL '{int(delta.total_seconds())} seconds'"),
            AnomalyDetection.detected_at,
        ).label("bucket")
        stmt = select(bucket, func.count().label("detections")).select_from(AnomalyDetection)
        stmt = self._detection_filters(stmt, start, end, zone, sensor, True)
        stmt = stmt.group_by(bucket).order_by(bucket.asc())
        return [{"timestamp": row.bucket, "detections": int(row.detections)} for row in self.session.execute(stmt)]

    def incident_counts(
        self,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool = True,
    ) -> dict[str, int]:
        stmt = select(
            func.count().label("created"),
            func.count().filter(Incident.status == "resolved").label("resolved"),
            func.count().filter(Incident.status == "false_alarm").label("false_alarms"),
        ).select_from(Incident)
        stmt = self._incident_filters(stmt, start, end, zone, sensor, inclusive_end, time_column=Incident.detected_at)
        row = self.session.execute(stmt).one()
        return {key: int(value or 0) for key, value in dict(row._mapping).items()}

    def incidents_grouped(
        self,
        column,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
    ) -> list[tuple[str, int]]:
        stmt = select(column, func.count()).select_from(Incident)
        stmt = self._incident_filters(stmt, start, end, zone, sensor, True, time_column=Incident.detected_at)
        stmt = stmt.group_by(column).order_by(column)
        return [(str(key), int(count)) for key, count in self.session.execute(stmt)]

    def incident_series(
        self,
        *,
        start: datetime,
        end: datetime,
        interval: str,
        zone: str | None,
        sensor: str | None,
    ) -> list[dict]:
        delta = INTERVAL_DELTAS[interval]
        bucket = func.time_bucket(
            literal_column(f"INTERVAL '{int(delta.total_seconds())} seconds'"),
            Incident.detected_at,
        ).label("bucket")
        stmt = select(bucket, func.count().label("incidents")).select_from(Incident)
        stmt = self._incident_filters(stmt, start, end, zone, sensor, True, time_column=Incident.detected_at)
        stmt = stmt.group_by(bucket).order_by(bucket.asc())
        return [{"timestamp": row.bucket, "incidents": int(row.incidents)} for row in self.session.execute(stmt)]

    def active_incident_count(self, *, as_of: datetime, zone: str | None, sensor: str | None) -> int:
        stmt = select(func.count()).select_from(Incident).where(
            Incident.detected_at <= as_of,
            (Incident.resolved_at.is_(None)) | (Incident.resolved_at > as_of),
        )
        stmt = self._apply_incident_scope(stmt, zone, sensor)
        return int(self.session.scalar(stmt) or 0)

    def duration_stats(
        self,
        start_column,
        end_column,
        *,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool = True,
    ) -> dict[str, float | None]:
        minutes = func.extract("epoch", end_column - start_column) / 60.0
        stmt = select(
            func.avg(minutes).label("mean_minutes"),
            func.percentile_cont(0.5).within_group(minutes).label("median_minutes"),
            func.count().label("sample_count"),
        ).select_from(Incident).where(
            start_column.is_not(None),
            end_column.is_not(None),
            end_column >= start_column,
        )
        stmt = self._incident_filters(stmt, start, end, zone, sensor, inclusive_end, time_column=start_column)
        row = self.session.execute(stmt).one()
        sample_count = int(row.sample_count or 0)
        if sample_count == 0:
            return {"mean_minutes": None, "median_minutes": None, "sample_count": 0}
        return {
            "mean_minutes": _round(row.mean_minutes, 1),
            "median_minutes": _round(row.median_minutes, 1),
            "sample_count": sample_count,
        }

    def response_series(
        self,
        *,
        start: datetime,
        end: datetime,
        interval: str,
        zone: str | None,
        sensor: str | None,
    ) -> list[dict]:
        delta = INTERVAL_DELTAS[interval]
        bucket = func.time_bucket(
            literal_column(f"INTERVAL '{int(delta.total_seconds())} seconds'"),
            Incident.detected_at,
        ).label("bucket")
        minutes = func.extract("epoch", Incident.response_started_at - Incident.detected_at) / 60.0
        stmt = (
            select(bucket, func.avg(minutes).label("mean_response_minutes"))
            .select_from(Incident)
            .where(Incident.response_started_at.is_not(None))
        )
        stmt = self._incident_filters(stmt, start, end, zone, sensor, True, time_column=Incident.detected_at)
        stmt = stmt.group_by(bucket).order_by(bucket.asc())
        return [
            {"timestamp": row.bucket, "mean_response_minutes": _round(row.mean_response_minutes, 1)}
            for row in self.session.execute(stmt)
        ]

    def task_counts(
        self,
        *,
        start: datetime,
        end: datetime,
        as_of: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool = True,
    ) -> dict[str, int]:
        open_stmt = select(func.count()).select_from(IncidentResponseTask).join(Incident)
        open_stmt = self._apply_incident_scope(open_stmt, zone, sensor)
        open_stmt = open_stmt.where(IncidentResponseTask.status.in_(OPEN_TASK_STATUSES))

        completed = select(func.count()).select_from(IncidentResponseTask).join(Incident)
        completed = self._apply_incident_scope(completed, zone, sensor)
        if inclusive_end:
            completed = completed.where(
                IncidentResponseTask.completed_at.is_not(None),
                IncidentResponseTask.completed_at >= start,
                IncidentResponseTask.completed_at <= end,
            )
        else:
            completed = completed.where(
                IncidentResponseTask.completed_at.is_not(None),
                IncidentResponseTask.completed_at >= start,
                IncidentResponseTask.completed_at < end,
            )

        overdue = select(func.count()).select_from(IncidentResponseTask).join(Incident)
        overdue = self._apply_incident_scope(overdue, zone, sensor)
        overdue = overdue.where(
            IncidentResponseTask.status.in_(OPEN_TASK_STATUSES),
            IncidentResponseTask.due_at.is_not(None),
            IncidentResponseTask.due_at < as_of,
        )
        return {
            "open_response_tasks": int(self.session.scalar(open_stmt) or 0),
            "completed_response_tasks": int(self.session.scalar(completed) or 0),
            "overdue_response_tasks": int(self.session.scalar(overdue) or 0),
        }

    def zone_rows(self, *, start: datetime, end: datetime, as_of: datetime, zone: str | None) -> list[dict]:
        sensor_alias = aliased(Asset)
        reading_sub = (
            select(
                Asset.zone_id.label("zone_id"),
                func.count().label("reading_count"),
                func.count(func.distinct(SensorReading.sensor_id)).label("reporting_sensors"),
                func.avg(SensorReading.pressure_kpa).label("avg_pressure_kpa"),
                func.avg(SensorReading.flow_lps).label("avg_flow_lps"),
            )
            .select_from(SensorReading)
            .join(Asset, SensorReading.sensor_id == Asset.id)
            .where(SensorReading.time >= start, SensorReading.time <= end)
            .group_by(Asset.zone_id)
            .subquery()
        )
        sensor_sub = (
            select(Asset.zone_id.label("zone_id"), func.count().label("selected_sensors"))
            .where(Asset.asset_type == "sensor")
            .group_by(Asset.zone_id)
            .subquery()
        )
        detection_sub = (
            select(sensor_alias.zone_id.label("zone_id"), func.count().label("detection_count"))
            .select_from(AnomalyDetection)
            .join(sensor_alias, AnomalyDetection.sensor_id == sensor_alias.id)
            .where(AnomalyDetection.detected_at >= start, AnomalyDetection.detected_at <= end)
            .group_by(sensor_alias.zone_id)
            .subquery()
        )
        incident_sub = (
            select(Incident.zone_id.label("zone_id"), func.count().label("active_incident_count"))
            .where(
                Incident.detected_at <= as_of,
                (Incident.resolved_at.is_(None)) | (Incident.resolved_at > as_of),
            )
            .group_by(Incident.zone_id)
            .subquery()
        )
        health_sub = (
            select(Asset.zone_id.label("zone_id"), func.avg(Asset.health_score).label("average_asset_health"))
            .group_by(Asset.zone_id)
            .subquery()
        )
        overdue_sub = (
            select(Incident.zone_id.label("zone_id"), func.count().label("overdue_response_tasks"))
            .select_from(IncidentResponseTask)
            .join(Incident, IncidentResponseTask.incident_id == Incident.id)
            .where(
                IncidentResponseTask.status.in_(OPEN_TASK_STATUSES),
                IncidentResponseTask.due_at.is_not(None),
                IncidentResponseTask.due_at < as_of,
            )
            .group_by(Incident.zone_id)
            .subquery()
        )
        stmt = (
            select(
                Zone.name,
                func.coalesce(reading_sub.c.reporting_sensors, 0),
                func.coalesce(sensor_sub.c.selected_sensors, 0),
                reading_sub.c.avg_pressure_kpa,
                reading_sub.c.avg_flow_lps,
                func.coalesce(detection_sub.c.detection_count, 0),
                func.coalesce(incident_sub.c.active_incident_count, 0),
                health_sub.c.average_asset_health,
                func.coalesce(overdue_sub.c.overdue_response_tasks, 0),
                func.coalesce(reading_sub.c.reading_count, 0),
            )
            .select_from(Zone)
            .outerjoin(reading_sub, reading_sub.c.zone_id == Zone.id)
            .outerjoin(sensor_sub, sensor_sub.c.zone_id == Zone.id)
            .outerjoin(detection_sub, detection_sub.c.zone_id == Zone.id)
            .outerjoin(incident_sub, incident_sub.c.zone_id == Zone.id)
            .outerjoin(health_sub, health_sub.c.zone_id == Zone.id)
            .outerjoin(overdue_sub, overdue_sub.c.zone_id == Zone.id)
            .order_by(Zone.name.asc())
        )
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        rows = []
        for row in self.session.execute(stmt):
            name, reporting, selected, pressure, flow, detections, incidents, health, overdue, readings = row
            expected = int(selected) * max(0, int((end - start).total_seconds() / SAMPLE_INTERVAL_SECONDS) + 1)
            completeness = None
            if expected > 0 and int(readings) > 0:
                completeness = round(min(100.0, (int(readings) / expected) * 100.0), 1)
            rows.append(
                {
                    "zone": name,
                    "reporting_sensors": int(reporting),
                    "selected_sensors": int(selected),
                    "telemetry_completeness_pct": completeness,
                    "average_pressure_bar": _scale(pressure, KPA_TO_BAR, 3) if int(readings) > 0 else None,
                    "average_flow_m3h": _scale(flow, LPS_TO_M3H, 2) if int(readings) > 0 else None,
                    "detection_count": int(detections),
                    "active_incident_count": int(incidents),
                    "average_asset_health": _round(health, 1),
                    "overdue_response_tasks": int(overdue),
                    "sufficient_data": int(readings) > 0 and int(reporting) > 0,
                }
            )
        return rows

    def asset_health_distribution(self, *, zone: str | None, sensor: str | None) -> dict:
        stmt = select(Asset.health_score, Asset.operational_status, Asset.asset_type).select_from(Asset)
        if zone:
            stmt = stmt.join(Zone, Asset.zone_id == Zone.id).where(func.lower(Zone.name) == zone.strip().casefold())
        if sensor:
            stmt = stmt.where(Asset.external_id == sensor)
        rows = list(self.session.execute(stmt))
        return {
            "health_scores": [row.health_score for row in rows],
            "statuses": [row.operational_status for row in rows],
            "types": [row.asset_type for row in rows],
        }

    def latest_reading_times(self, sensor_ids: list[UUID]) -> dict[UUID, datetime]:
        if not sensor_ids:
            return {}
        rows = self.session.execute(
            select(SensorReading.sensor_id, func.max(SensorReading.time)).where(SensorReading.sensor_id.in_(sensor_ids)).group_by(SensorReading.sensor_id)
        )
        return {sensor_id: latest for sensor_id, latest in rows}

    def _detection_filters(
        self,
        stmt: Select,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool,
        *,
        already_from_detection: bool = False,
    ) -> Select:
        _ = already_from_detection
        if inclusive_end:
            stmt = stmt.where(AnomalyDetection.detected_at >= start, AnomalyDetection.detected_at <= end)
        else:
            stmt = stmt.where(AnomalyDetection.detected_at >= start, AnomalyDetection.detected_at < end)
        if zone or sensor:
            stmt = stmt.join(Asset, AnomalyDetection.sensor_id == Asset.id)
        if zone:
            stmt = stmt.join(Zone, Asset.zone_id == Zone.id).where(func.lower(Zone.name) == zone.strip().casefold())
        if sensor:
            stmt = stmt.where(Asset.external_id == sensor)
        return stmt

    def _incident_filters(
        self,
        stmt: Select,
        start: datetime,
        end: datetime,
        zone: str | None,
        sensor: str | None,
        inclusive_end: bool,
        *,
        time_column,
    ) -> Select:
        if inclusive_end:
            stmt = stmt.where(time_column >= start, time_column <= end)
        else:
            stmt = stmt.where(time_column >= start, time_column < end)
        return self._apply_incident_scope(stmt, zone, sensor)

    def _apply_incident_scope(self, stmt: Select, zone: str | None, sensor: str | None) -> Select:
        if zone:
            stmt = stmt.join(Zone, Incident.zone_id == Zone.id).where(func.lower(Zone.name) == zone.strip().casefold())
        if sensor:
            stmt = stmt.outerjoin(Asset, Incident.sensor_id == Asset.id).where(Asset.external_id == sensor)
        return stmt


def _scale(value: float | None, factor: float, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value) * factor, digits)


def _round(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)
