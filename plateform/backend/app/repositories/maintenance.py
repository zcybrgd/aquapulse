from datetime import datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Asset, Incident, Zone
from app.db.models.maintenance import MaintenancePlan, MaintenanceWorkOrder, MaintenanceWorkOrderEvent
from app.maintenance.workflow import OPEN_STATUSES, PRIORITY_RANK, TERMINAL_STATUSES
from app.schemas.assets import AssetType
from app.schemas.incidents import SortOrder
from app.schemas.maintenance import (
    MaintenancePriority,
    MaintenanceType,
    WorkOrderSortField,
    WorkOrderStatus,
)

PRIORITY_ORDER = case(
    (MaintenanceWorkOrder.priority == "critical", 4),
    (MaintenanceWorkOrder.priority == "high", 3),
    (MaintenanceWorkOrder.priority == "medium", 2),
    else_=1,
)

DETAIL_OPTIONS = (
    joinedload(MaintenanceWorkOrder.asset).joinedload(Asset.zone),
    joinedload(MaintenanceWorkOrder.plan),
    joinedload(MaintenanceWorkOrder.incident),
    selectinload(MaintenanceWorkOrder.events),
)


class MaintenanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_plan_public_id(self) -> str:
        return self._next_id(MaintenancePlan.public_id, "MPLAN-")

    def next_work_order_public_id(self) -> str:
        return self._next_id(MaintenanceWorkOrder.public_id, "MWO-")

    def next_event_public_id(self) -> str:
        return self._next_id(MaintenanceWorkOrderEvent.public_id, "MWE-")

    def _next_id(self, column, prefix: str) -> str:
        numbers = list(self.session.scalars(select(column)).all())
        existing = {item.upper() for item in numbers if item}
        highest = 0
        for number in numbers:
            if not number or not number.upper().startswith(prefix.upper()):
                continue
            suffix = number[len(prefix) :]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        candidate = highest + 1
        while f"{prefix}{candidate:06d}".upper() in existing:
            candidate += 1
        return f"{prefix}{candidate:06d}"

    def get_plan(self, plan_id: str) -> MaintenancePlan | None:
        stmt = (
            select(MaintenancePlan)
            .options(joinedload(MaintenancePlan.asset).joinedload(Asset.zone))
            .where(func.upper(MaintenancePlan.public_id) == plan_id.strip().upper())
        )
        return self.session.scalars(stmt).unique().first()

    def get_plan_for_update(self, plan_id: str) -> MaintenancePlan | None:
        stmt = (
            select(MaintenancePlan)
            .where(func.upper(MaintenancePlan.public_id) == plan_id.strip().upper())
            .with_for_update()
        )
        return self.session.scalars(stmt).first()

    def get_work_order(self, work_order_id: str) -> MaintenanceWorkOrder | None:
        stmt = (
            select(MaintenanceWorkOrder)
            .options(*DETAIL_OPTIONS)
            .where(func.upper(MaintenanceWorkOrder.public_id) == work_order_id.strip().upper())
        )
        return self.session.scalars(stmt).unique().first()

    def get_work_order_for_update(self, work_order_id: str) -> MaintenanceWorkOrder | None:
        stmt = (
            select(MaintenanceWorkOrder)
            .where(func.upper(MaintenanceWorkOrder.public_id) == work_order_id.strip().upper())
            .with_for_update()
        )
        return self.session.scalars(stmt).first()

    def list_plans(self, *, asset_id: str | None = None, enabled: bool | None = None) -> list[MaintenancePlan]:
        stmt = select(MaintenancePlan).options(joinedload(MaintenancePlan.asset).joinedload(Asset.zone))
        if asset_id:
            stmt = stmt.join(Asset, MaintenancePlan.asset_id == Asset.id).where(
                func.upper(Asset.external_id) == asset_id.strip().upper()
            )
        if enabled is not None:
            stmt = stmt.where(MaintenancePlan.enabled.is_(enabled))
        stmt = stmt.order_by(MaintenancePlan.next_due_at.asc(), MaintenancePlan.public_id.asc())
        return list(self.session.scalars(stmt).unique().all())

    def list_enabled_due_plans(self, as_of: datetime) -> list[MaintenancePlan]:
        stmt = (
            select(MaintenancePlan)
            .options(selectinload(MaintenancePlan.asset))
            .where(MaintenancePlan.enabled.is_(True), MaintenancePlan.next_due_at <= as_of)
            .order_by(MaintenancePlan.next_due_at.asc(), MaintenancePlan.public_id.asc())
            .with_for_update(of=MaintenancePlan)
        )
        return list(self.session.scalars(stmt).unique().all())

    def has_open_work_order_for_plan(self, plan_id) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.maintenance_plan_id == plan_id,
                    MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)),
                )
            )
            or 0
        ) > 0

    def list_work_orders(
        self,
        *,
        status: WorkOrderStatus | None = None,
        priority: MaintenancePriority | None = None,
        maintenance_type: MaintenanceType | None = None,
        asset_type: AssetType | None = None,
        asset_id: str | None = None,
        zone: str | None = None,
        assigned_to: str | None = None,
        overdue: bool | None = None,
        due_from: datetime | None = None,
        due_to: datetime | None = None,
        search: str | None = None,
        incident_id: str | None = None,
        sort_by: WorkOrderSortField = WorkOrderSortField.due_at,
        sort_order: SortOrder = SortOrder.asc,
        reference_time: datetime,
    ) -> list[MaintenanceWorkOrder]:
        stmt = (
            select(MaintenanceWorkOrder)
            .join(Asset, MaintenanceWorkOrder.asset_id == Asset.id)
            .join(Zone, Asset.zone_id == Zone.id)
            .outerjoin(Incident, MaintenanceWorkOrder.incident_id == Incident.id)
            .options(
                joinedload(MaintenanceWorkOrder.asset).joinedload(Asset.zone),
                joinedload(MaintenanceWorkOrder.plan),
                joinedload(MaintenanceWorkOrder.incident),
            )
        )
        if status is not None:
            stmt = stmt.where(MaintenanceWorkOrder.status == status.value)
        if priority is not None:
            stmt = stmt.where(MaintenanceWorkOrder.priority == priority.value)
        if maintenance_type is not None:
            stmt = stmt.where(MaintenanceWorkOrder.maintenance_type == maintenance_type.value)
        if asset_type is not None:
            stmt = stmt.where(Asset.asset_type == asset_type.value)
        if asset_id:
            stmt = stmt.where(func.upper(Asset.external_id) == asset_id.strip().upper())
        if zone:
            stmt = stmt.where(func.lower(Zone.name) == zone.strip().casefold())
        if assigned_to:
            stmt = stmt.where(func.lower(MaintenanceWorkOrder.assigned_to) == assigned_to.strip().casefold())
        if incident_id:
            stmt = stmt.where(func.upper(Incident.incident_number) == incident_id.strip().upper())
        if due_from is not None:
            stmt = stmt.where(MaintenanceWorkOrder.due_at >= due_from)
        if due_to is not None:
            stmt = stmt.where(MaintenanceWorkOrder.due_at <= due_to)
        if overdue is True:
            stmt = stmt.where(
                MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)),
                MaintenanceWorkOrder.due_at < reference_time,
            )
        elif overdue is False:
            stmt = stmt.where(
                or_(
                    MaintenanceWorkOrder.status.in_(tuple(TERMINAL_STATUSES)),
                    MaintenanceWorkOrder.due_at >= reference_time,
                )
            )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    MaintenanceWorkOrder.public_id.ilike(pattern),
                    MaintenanceWorkOrder.title.ilike(pattern),
                    MaintenanceWorkOrder.description.ilike(pattern),
                    Asset.external_id.ilike(pattern),
                    Asset.name.ilike(pattern),
                    Asset.location_label.ilike(pattern),
                    Zone.name.ilike(pattern),
                )
            )
        descending = sort_order == SortOrder.desc
        stmt = stmt.order_by(*self._order_by(sort_by, descending))
        return list(self.session.scalars(stmt).unique().all())

    def list_open_for_asset(self, asset_uuid) -> list[MaintenanceWorkOrder]:
        stmt = (
            select(MaintenanceWorkOrder)
            .options(
                joinedload(MaintenanceWorkOrder.asset).joinedload(Asset.zone),
                joinedload(MaintenanceWorkOrder.plan),
                joinedload(MaintenanceWorkOrder.incident),
            )
            .where(
                MaintenanceWorkOrder.asset_id == asset_uuid,
                MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)),
            )
            .order_by(MaintenanceWorkOrder.due_at.asc())
        )
        return list(self.session.scalars(stmt).unique().all())

    def list_recent_completed_for_asset(self, asset_uuid, *, limit: int = 5) -> list[MaintenanceWorkOrder]:
        stmt = (
            select(MaintenanceWorkOrder)
            .options(
                joinedload(MaintenanceWorkOrder.asset).joinedload(Asset.zone),
                joinedload(MaintenanceWorkOrder.plan),
                joinedload(MaintenanceWorkOrder.incident),
            )
            .where(
                MaintenanceWorkOrder.asset_id == asset_uuid,
                MaintenanceWorkOrder.status == WorkOrderStatus.completed.value,
            )
            .order_by(MaintenanceWorkOrder.completed_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).unique().all())

    def list_history(self, work_order_uuid) -> list[MaintenanceWorkOrderEvent]:
        stmt = (
            select(MaintenanceWorkOrderEvent)
            .where(MaintenanceWorkOrderEvent.work_order_id == work_order_uuid)
            .order_by(MaintenanceWorkOrderEvent.created_at.asc(), MaintenanceWorkOrderEvent.public_id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def enabled_plans_for_asset(self, asset_uuid) -> list[MaintenancePlan]:
        stmt = (
            select(MaintenancePlan)
            .options(joinedload(MaintenancePlan.asset).joinedload(Asset.zone))
            .where(MaintenancePlan.asset_id == asset_uuid, MaintenancePlan.enabled.is_(True))
            .order_by(MaintenancePlan.next_due_at.asc())
        )
        return list(self.session.scalars(stmt).unique().all())

    def assets_without_enabled_plan_count(self) -> int:
        planned = select(MaintenancePlan.asset_id).where(MaintenancePlan.enabled.is_(True)).distinct()
        return (
            self.session.scalar(select(func.count()).select_from(Asset).where(Asset.id.not_in(planned)))
            or 0
        )

    def count_open_by_status(self, status: str) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(MaintenanceWorkOrder.status == status)
            )
            or 0
        )

    def count_overdue(self, reference_time: datetime) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)),
                    MaintenanceWorkOrder.due_at < reference_time,
                )
            )
            or 0
        )

    def count_due_within(self, reference_time: datetime, days: int) -> int:
        until = reference_time + timedelta(days=days)
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)),
                    MaintenanceWorkOrder.due_at >= reference_time,
                    MaintenanceWorkOrder.due_at <= until,
                )
            )
            or 0
        )

    def count_completed_since(self, start: datetime) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.status == WorkOrderStatus.completed.value,
                    MaintenanceWorkOrder.completed_at.is_not(None),
                    MaintenanceWorkOrder.completed_at >= start,
                )
            )
            or 0
        )

    def count_open_critical(self) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(
                    MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)),
                    MaintenanceWorkOrder.priority == "critical",
                )
            )
            or 0
        )

    def count_open(self) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MaintenanceWorkOrder)
                .where(MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)))
            )
            or 0
        )

    def list_upcoming(self, reference_time: datetime, *, limit: int = 12) -> list[MaintenanceWorkOrder]:
        stmt = (
            select(MaintenanceWorkOrder)
            .options(
                joinedload(MaintenanceWorkOrder.asset).joinedload(Asset.zone),
                joinedload(MaintenanceWorkOrder.plan),
            )
            .where(MaintenanceWorkOrder.status.in_(tuple(OPEN_STATUSES)))
            .order_by(MaintenanceWorkOrder.due_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).unique().all())

    def _order_by(self, sort_by: WorkOrderSortField, descending: bool):
        due = MaintenanceWorkOrder.due_at.desc() if descending else MaintenanceWorkOrder.due_at.asc()
        public_id = MaintenanceWorkOrder.public_id.asc()
        if sort_by == WorkOrderSortField.priority:
            column = PRIORITY_ORDER.desc() if descending else PRIORITY_ORDER.asc()
            return (column, due, public_id)
        if sort_by == WorkOrderSortField.status:
            column = MaintenanceWorkOrder.status.desc() if descending else MaintenanceWorkOrder.status.asc()
            return (column, due, public_id)
        if sort_by == WorkOrderSortField.created_at:
            column = MaintenanceWorkOrder.created_at.desc() if descending else MaintenanceWorkOrder.created_at.asc()
            return (column, public_id)
        if sort_by == WorkOrderSortField.asset_name:
            column = Asset.name.desc() if descending else Asset.name.asc()
            return (column, due, public_id)
        return (due, public_id)


_ = PRIORITY_RANK
