from datetime import datetime

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_AsGeoJSON, ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import Select, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Asset, Incident, PipelineSegment, Zone
from app.schemas.assets import AssetType, OperationalStatus
from app.schemas.incidents import IncidentStatus, SeverityTier
from app.services.incidents import ACTIVE_STATUSES

EXCLUDED_INCIDENT_STATUSES = {
    IncidentStatus.resolved.value,
}


class MapRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_zones(self, *, zone: str | None = None) -> list[tuple[Zone, str, int, int]]:
        asset_count = (
            select(func.count(Asset.id))
            .where(Asset.zone_id == Zone.id)
            .correlate(Zone)
            .scalar_subquery()
        )
        incident_count = (
            select(func.count(Incident.id))
            .where(
                Incident.zone_id == Zone.id,
                Incident.status.in_(ACTIVE_STATUSES),
            )
            .correlate(Zone)
            .scalar_subquery()
        )
        stmt = (
            select(Zone, ST_AsGeoJSON(Zone.boundary), asset_count, incident_count)
            .where(Zone.boundary.is_not(None))
            .order_by(Zone.name)
        )
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        return list(self.session.execute(stmt).all())

    def list_pipelines(self, *, zone: str | None = None) -> list[tuple]:
        incident_count = (
            select(func.count(Incident.id))
            .where(
                Incident.pipeline_segment_id == PipelineSegment.id,
                Incident.status.in_(ACTIVE_STATUSES),
            )
            .correlate(PipelineSegment)
            .scalar_subquery()
        )
        asset_count = (
            select(func.count(Asset.id))
            .where(Asset.pipeline_segment_id == PipelineSegment.id)
            .correlate(PipelineSegment)
            .scalar_subquery()
        )
        stmt = (
            select(
                PipelineSegment,
                Zone.name,
                ST_AsGeoJSON(PipelineSegment.geometry),
                incident_count,
                asset_count,
            )
            .join(Zone, PipelineSegment.zone_id == Zone.id)
            .where(PipelineSegment.geometry.is_not(None))
            .order_by(PipelineSegment.name)
        )
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        return list(self.session.execute(stmt).all())

    def list_assets(
        self,
        *,
        zone: str | None = None,
        asset_type: AssetType | None = None,
        asset_status: OperationalStatus | None = None,
    ) -> list[tuple]:
        incident_count = (
            select(func.count(Incident.id))
            .where(
                or_(Incident.sensor_id == Asset.id, Incident.valve_id == Asset.id),
                Incident.status.in_(ACTIVE_STATUSES),
            )
            .correlate(Asset)
            .scalar_subquery()
        )
        stmt = (
            select(
                Asset,
                Zone.name,
                PipelineSegment.name,
                PipelineSegment.external_id,
                ST_AsGeoJSON(Asset.location),
                incident_count,
            )
            .join(Zone, Asset.zone_id == Zone.id)
            .outerjoin(PipelineSegment, Asset.pipeline_segment_id == PipelineSegment.id)
            .options(selectinload(Asset.zone), selectinload(Asset.pipeline_segment))
            .where(Asset.location.is_not(None))
            .order_by(Asset.name)
        )
        stmt = self._apply_asset_filters(stmt, zone=zone, asset_type=asset_type, asset_status=asset_status)
        return list(self.session.execute(stmt).all())

    def list_incidents(
        self,
        *,
        zone: str | None = None,
        incident_severity: SeverityTier | None = None,
        incident_status: IncidentStatus | None = None,
        include_resolved: bool = False,
    ) -> list[tuple]:
        point = ST_SetSRID(ST_MakePoint(Incident.longitude, Incident.latitude), 4326)
        stmt = (
            select(
                Incident,
                Asset.external_id,
                PipelineSegment.external_id,
                ST_AsGeoJSON(point),
            )
            .outerjoin(Asset, Incident.sensor_id == Asset.id)
            .outerjoin(PipelineSegment, Incident.pipeline_segment_id == PipelineSegment.id)
            .join(Zone, Incident.zone_id == Zone.id)
            .order_by(Incident.detected_at.desc())
        )
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if incident_severity is not None:
            stmt = stmt.where(Incident.severity_tier == int(incident_severity.value.split("_")[1]))
        if incident_status is not None:
            stmt = stmt.where(Incident.status == incident_status.value)
        elif not include_resolved:
            stmt = stmt.where(Incident.status.notin_(EXCLUDED_INCIDENT_STATUSES))
        return list(self.session.execute(stmt).all())

    def summary_timestamp(self) -> datetime | None:
        asset_ts = self.session.scalar(select(func.max(Asset.updated_at)))
        incident_ts = self.session.scalar(select(func.max(Incident.updated_at)))
        values = [value for value in (asset_ts, incident_ts) if value is not None]
        return max(values) if values else None

    def nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: float,
        feature_type: str | None,
    ) -> list[tuple[str, object, str, float, object, object]]:
        origin = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        origin_geog = cast(origin, Geography)
        rows: list[tuple] = []

        if feature_type in (None, "asset"):
            distance = ST_Distance(cast(Asset.location, Geography), origin_geog)
            stmt = (
                select(
                    Asset,
                    Zone.name,
                    PipelineSegment.name,
                    PipelineSegment.external_id,
                    ST_AsGeoJSON(Asset.location),
                    distance,
                )
                .join(Zone, Asset.zone_id == Zone.id)
                .outerjoin(PipelineSegment, Asset.pipeline_segment_id == PipelineSegment.id)
                .options(selectinload(Asset.zone), selectinload(Asset.pipeline_segment))
                .where(
                    Asset.location.is_not(None),
                    ST_DWithin(cast(Asset.location, Geography), origin_geog, radius_m),
                )
                .order_by(distance)
            )
            for row in self.session.execute(stmt):
                rows.append(("asset", row))

        if feature_type in (None, "pipeline"):
            distance = ST_Distance(cast(PipelineSegment.geometry, Geography), origin_geog)
            stmt = (
                select(
                    PipelineSegment,
                    Zone.name,
                    ST_AsGeoJSON(PipelineSegment.geometry),
                    distance,
                )
                .join(Zone, PipelineSegment.zone_id == Zone.id)
                .where(
                    PipelineSegment.geometry.is_not(None),
                    ST_DWithin(cast(PipelineSegment.geometry, Geography), origin_geog, radius_m),
                )
                .order_by(distance)
            )
            for row in self.session.execute(stmt):
                rows.append(("pipeline", row))

        if feature_type in (None, "incident"):
            point = ST_SetSRID(ST_MakePoint(Incident.longitude, Incident.latitude), 4326)
            distance = ST_Distance(cast(point, Geography), origin_geog)
            stmt = (
                select(
                    Incident,
                    Asset.external_id,
                    PipelineSegment.external_id,
                    ST_AsGeoJSON(point),
                    distance,
                )
                .outerjoin(Asset, Incident.sensor_id == Asset.id)
                .outerjoin(PipelineSegment, Incident.pipeline_segment_id == PipelineSegment.id)
                .where(
                    Incident.status.notin_(EXCLUDED_INCIDENT_STATUSES),
                    ST_DWithin(cast(point, Geography), origin_geog, radius_m),
                )
                .order_by(distance)
            )
            for row in self.session.execute(stmt):
                rows.append(("incident", row))

        return rows

    def _apply_asset_filters(
        self,
        stmt: Select,
        *,
        zone: str | None,
        asset_type: AssetType | None,
        asset_status: OperationalStatus | None,
    ) -> Select:
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if asset_type is not None:
            stmt = stmt.where(Asset.asset_type == asset_type.value)
        if asset_status is not None:
            stmt = stmt.where(Asset.operational_status == asset_status.value)
        return stmt
