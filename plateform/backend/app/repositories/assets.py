from datetime import datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Asset, Incident, PipelineSegment, Zone
from app.schemas.assets import AssetSortField, AssetType, MaintenanceFilter, OperationalStatus
from app.schemas.incidents import SortOrder

STATUS_RANK = case(
    (Asset.operational_status == OperationalStatus.online.value, 3),
    (Asset.operational_status == OperationalStatus.degraded.value, 2),
    (Asset.operational_status == OperationalStatus.offline.value, 1),
    else_=0,
)

LIST_OPTIONS = (
    joinedload(Asset.zone),
    joinedload(Asset.pipeline_segment),
)

DETAIL_OPTIONS = (
    *LIST_OPTIONS,
    selectinload(Asset.incidents_as_sensor).joinedload(Incident.zone),
    selectinload(Asset.incidents_as_sensor).joinedload(Incident.pipeline_segment),
    selectinload(Asset.incidents_as_valve).joinedload(Incident.zone),
    selectinload(Asset.incidents_as_valve).joinedload(Incident.pipeline_segment),
)


class AssetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_assets(
        self,
        *,
        asset_type: AssetType | None = None,
        status: OperationalStatus | None = None,
        zone: str | None = None,
        search: str | None = None,
        maintenance: MaintenanceFilter | None = None,
        sort_by: AssetSortField = AssetSortField.health_score,
        sort_order: SortOrder = SortOrder.asc,
        now: datetime,
    ) -> list[Asset]:
        stmt = (
            select(Asset)
            .join(Zone, Asset.zone_id == Zone.id)
            .outerjoin(PipelineSegment, Asset.pipeline_segment_id == PipelineSegment.id)
            .options(*LIST_OPTIONS)
        )
        if asset_type is not None:
            stmt = stmt.where(Asset.asset_type == asset_type.value)
        if status is not None:
            stmt = stmt.where(Asset.operational_status == status.value)
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Asset.external_id.ilike(pattern),
                    Asset.name.ilike(pattern),
                    Asset.manufacturer.ilike(pattern),
                    Asset.model.ilike(pattern),
                    Asset.serial_number.ilike(pattern),
                    Asset.location_label.ilike(pattern),
                    Zone.name.ilike(pattern),
                    Zone.code.ilike(pattern),
                )
            )
        if maintenance == MaintenanceFilter.due:
            stmt = stmt.where(Asset.next_maintenance_at.is_not(None), Asset.next_maintenance_at <= now)
        elif maintenance == MaintenanceFilter.upcoming:
            upcoming_until = now + timedelta(days=30)
            stmt = stmt.where(
                Asset.next_maintenance_at.is_not(None),
                Asset.next_maintenance_at > now,
                Asset.next_maintenance_at <= upcoming_until,
            )
        elif maintenance == MaintenanceFilter.scheduled:
            stmt = stmt.where(Asset.next_maintenance_at.is_not(None), Asset.next_maintenance_at > now)

        descending = sort_order == SortOrder.desc
        stmt = stmt.order_by(*self._order_by(sort_by, descending))
        return list(self.session.scalars(stmt).unique().all())

    def get_by_external_id(self, external_id: str) -> Asset | None:
        stmt = (
            select(Asset)
            .where(func.upper(Asset.external_id) == external_id.strip().upper())
            .options(*DETAIL_OPTIONS)
        )
        return self.session.scalars(stmt).unique().first()

    def list_related_incidents(self, asset: Asset) -> list[Incident]:
        if asset.asset_type == AssetType.sensor.value:
            rows = list(asset.incidents_as_sensor)
        elif asset.asset_type == AssetType.valve.value:
            rows = list(asset.incidents_as_valve)
        else:
            stmt = (
                select(Incident)
                .where(Incident.zone_id == asset.zone_id)
                .options(joinedload(Incident.zone), joinedload(Incident.pipeline_segment))
                .order_by(Incident.detected_at.desc())
            )
            rows = list(self.session.scalars(stmt).unique().all())
        return sorted(rows, key=lambda incident: incident.detected_at, reverse=True)

    def sensor_counts(self) -> tuple[int, int]:
        total = self.session.scalar(
            select(func.count()).select_from(Asset).where(Asset.asset_type == AssetType.sensor.value)
        ) or 0
        online = self.session.scalar(
            select(func.count())
            .select_from(Asset)
            .where(
                Asset.asset_type == AssetType.sensor.value,
                Asset.operational_status == OperationalStatus.online.value,
            )
        ) or 0
        return int(online), int(total)

    def _order_by(self, sort_by: AssetSortField, descending: bool):
        name = Asset.name.desc() if descending else Asset.name.asc()
        if sort_by == AssetSortField.asset_type:
            column = Asset.asset_type.desc() if descending else Asset.asset_type.asc()
            return (column, name)
        if sort_by == AssetSortField.status:
            column = STATUS_RANK.desc() if descending else STATUS_RANK.asc()
            return (column, name)
        if sort_by == AssetSortField.health_score:
            column = Asset.health_score.desc().nulls_last() if descending else Asset.health_score.asc().nulls_last()
            return (column, name)
        if sort_by == AssetSortField.last_seen:
            column = Asset.last_seen_at.desc().nulls_last() if descending else Asset.last_seen_at.asc().nulls_last()
            return (column, name)
        if sort_by == AssetSortField.next_maintenance:
            column = (
                Asset.next_maintenance_at.desc().nulls_last()
                if descending
                else Asset.next_maintenance_at.asc().nulls_last()
            )
            return (column, name)
        return (name,)
