"""Human maintenance workflow. No physical command is executed.

actor_name is a temporary development identity, not authentication.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.assets.connectivity import mask_device_msisdn, public_zone_id
from app.core.exceptions import (
    AssetNotFoundError,
    DatabaseUnavailableError,
    IncidentNotFoundError,
    MaintenanceConflictError,
    MaintenancePlanNotFoundError,
    MaintenanceWorkOrderNotFoundError,
)
from app.data.incidents import SEED_NOW
from app.db.base import utc_now
from app.db.models import Asset, Incident
from app.db.models.maintenance import MaintenancePlan, MaintenanceWorkOrder, MaintenanceWorkOrderEvent
from app.maintenance.workflow import (
    ASSIGN_STATUSES,
    CANCEL_STATUSES,
    COMPLETE_STATUSES,
    NOTE_STATUSES,
    OPEN_STATUSES,
    RESCHEDULE_STATUSES,
    START_STATUSES,
    SUCCESSFUL_COMPLETION_RESULTS,
    TERMINAL_STATUSES,
    UNCHANGED_ASSET_RESULTS,
    allowed_actions,
    is_overdue,
)
from app.repositories.assets import AssetRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.maintenance import MaintenanceRepository
from app.schemas.assets import AssetType
from app.schemas.incidents import SortOrder
from app.schemas.maintenance import (
    AssetMaintenanceResponse,
    AssignWorkOrderRequest,
    CancelWorkOrderRequest,
    CompleteWorkOrderRequest,
    CreatePlanRequest,
    CreateWorkOrderRequest,
    DisablePlanRequest,
    IncidentMaintenanceResponse,
    MaintenanceNoteRequest,
    MaintenancePlanListResponse,
    MaintenancePlanSummary,
    MaintenancePriority,
    MaintenanceSummary,
    MaintenanceType,
    RescheduleWorkOrderRequest,
    StartWorkOrderRequest,
    UpdatePlanRequest,
    UpcomingMaintenanceItem,
    WorkOrderDetail,
    WorkOrderHistoryEvent,
    WorkOrderHistoryResponse,
    WorkOrderListResponse,
    WorkOrderSortField,
    WorkOrderStatus,
    WorkOrderSummary,
)

REFERENCE_TIME = SEED_NOW


class MaintenanceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = MaintenanceRepository(session)
        self.assets = AssetRepository(session)
        self.incidents = IncidentRepository(session)

    def reference_time(self) -> datetime:
        return REFERENCE_TIME

    def summary(self) -> MaintenanceSummary:
        now = self.reference_time()
        try:
            return MaintenanceSummary(
                overdue=self.repository.count_overdue(now),
                due_within_7_days=self.repository.count_due_within(now, 7),
                in_progress=self.repository.count_open_by_status(WorkOrderStatus.in_progress.value),
                completed_in_period=self.repository.count_completed_since(now - timedelta(days=30)),
                critical=self.repository.count_open_critical(),
                assets_without_plan=self.repository.assets_without_enabled_plan_count(),
                open_work_orders=self.repository.count_open(),
                reference_time=now,
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc

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
        sort_by: WorkOrderSortField = WorkOrderSortField.due_at,
        sort_order: SortOrder = SortOrder.asc,
    ) -> WorkOrderListResponse:
        now = self.reference_time()
        try:
            rows = self.repository.list_work_orders(
                status=status,
                priority=priority,
                maintenance_type=maintenance_type,
                asset_type=asset_type,
                asset_id=asset_id,
                zone=zone,
                assigned_to=assigned_to,
                overdue=overdue,
                due_from=due_from,
                due_to=due_to,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
                reference_time=now,
            )
            summary = self.summary()
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        return WorkOrderListResponse(
            items=[self._to_summary(row, now) for row in rows],
            total=len(rows),
            summary=summary,
            reference_time=now,
        )

    def get_work_order(self, work_order_id: str) -> WorkOrderDetail:
        now = self.reference_time()
        row = self._load_work_order(work_order_id)
        history = [self._to_event(item) for item in self.repository.list_history(row.id)]
        return WorkOrderDetail(**self._to_summary(row, now).model_dump(), history=history)

    def get_history(self, work_order_id: str) -> WorkOrderHistoryResponse:
        row = self._load_work_order(work_order_id)
        items = [self._to_event(item) for item in self.repository.list_history(row.id)]
        return WorkOrderHistoryResponse(work_order_id=row.public_id, items=items, total=len(items))

    def create_work_order(self, payload: CreateWorkOrderRequest) -> WorkOrderDetail:
        asset = self._require_asset(payload.asset_id)
        plan = None
        if payload.maintenance_plan_id:
            plan = self._lock_plan(payload.maintenance_plan_id)
            if not plan.enabled:
                raise MaintenanceConflictError(
                    f"Maintenance plan {plan.public_id} is disabled.",
                    code="maintenance_plan_disabled",
                )
            if plan.asset_id != asset.id:
                raise MaintenanceConflictError(
                    "The selected plan does not belong to this asset.",
                    code="invalid_maintenance_transition",
                )
            if self.repository.has_open_work_order_for_plan(plan.id):
                raise MaintenanceConflictError(
                    f"Plan {plan.public_id} already has an open work order.",
                    code="maintenance_duplicate_open_order",
                )
        incident = self._optional_incident(payload.incident_id)
        assigned = payload.assigned_to
        status = WorkOrderStatus.assigned.value if assigned else WorkOrderStatus.scheduled.value
        row = MaintenanceWorkOrder(
            id=uuid4(),
            public_id=self.repository.next_work_order_public_id(),
            asset_id=asset.id,
            maintenance_plan_id=plan.id if plan is not None else None,
            incident_id=incident.id if incident is not None else None,
            maintenance_type=payload.maintenance_type.value,
            title=payload.title,
            description=payload.description,
            priority=payload.priority.value,
            status=status,
            assigned_to=assigned,
            scheduled_start_at=payload.scheduled_start_at,
            due_at=payload.due_at,
            created_by=payload.actor_name,
        )
        self.session.add(row)
        self.session.flush()
        self._append_event(
            row,
            event_type="work_order_created",
            actor_name=payload.actor_name,
            from_status=None,
            to_status=status,
            note=payload.description,
            plan=plan,
        )
        if assigned:
            self._append_event(
                row,
                event_type="work_order_assigned",
                actor_name=payload.actor_name,
                from_status=WorkOrderStatus.scheduled.value,
                to_status=status,
                note=f"Assigned to {assigned}",
            )
        self._commit()
        return self.get_work_order(row.public_id)

    def assign(self, work_order_id: str, payload: AssignWorkOrderRequest) -> WorkOrderDetail:
        row = self._lock_work_order(work_order_id)
        if row.status not in ASSIGN_STATUSES:
            self._conflict(row, action="assign")
        previous = row.status
        row.assigned_to = payload.assigned_to
        row.status = WorkOrderStatus.assigned.value
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="work_order_assigned",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status=row.status,
            note=payload.note or f"Assigned to {payload.assigned_to}",
        )
        self._commit()
        return self.get_work_order(row.public_id)

    def reschedule(self, work_order_id: str, payload: RescheduleWorkOrderRequest) -> WorkOrderDetail:
        row = self._lock_work_order(work_order_id)
        if row.status not in RESCHEDULE_STATUSES:
            self._conflict(row, action="reschedule")
        row.due_at = payload.due_at
        if payload.scheduled_start_at is not None:
            row.scheduled_start_at = payload.scheduled_start_at
        row.updated_at = utc_now()
        self._append_event(
            row,
            event_type="work_order_rescheduled",
            actor_name=payload.actor_name,
            from_status=row.status,
            to_status=row.status,
            note=payload.note or f"Rescheduled due {payload.due_at.isoformat()}",
            metadata={"due_at": payload.due_at.isoformat()},
        )
        self._commit()
        return self.get_work_order(row.public_id)

    def start(self, work_order_id: str, payload: StartWorkOrderRequest) -> WorkOrderDetail:
        row = self._lock_work_order(work_order_id)
        if row.status not in START_STATUSES:
            self._conflict(row, action="start")
        if not row.assigned_to and not payload.assigned_to and not payload.confirm_unassigned:
            raise MaintenanceConflictError(
                "Starting an unassigned work order requires an assignment or explicit confirmation.",
                code="maintenance_assignment_required",
            )
        previous = row.status
        if payload.assigned_to:
            row.assigned_to = payload.assigned_to
            row.status = WorkOrderStatus.assigned.value
            self._append_event(
                row,
                event_type="work_order_assigned",
                actor_name=payload.actor_name,
                from_status=previous,
                to_status=row.status,
                note=f"Assigned to {payload.assigned_to}",
            )
            previous = row.status
        now = utc_now()
        row.status = WorkOrderStatus.in_progress.value
        row.started_at = now
        row.updated_at = now
        self._append_event(
            row,
            event_type="work_started",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status=row.status,
            note=payload.note,
        )
        self._commit()
        return self.get_work_order(row.public_id)

    def add_note(self, work_order_id: str, payload: MaintenanceNoteRequest) -> WorkOrderDetail:
        row = self._lock_work_order(work_order_id)
        if row.status not in NOTE_STATUSES:
            self._conflict(row, action="add_note")
        self._append_event(
            row,
            event_type="note_added",
            actor_name=payload.actor_name,
            from_status=row.status,
            to_status=row.status,
            note=payload.note,
        )
        row.updated_at = utc_now()
        self._commit()
        return self.get_work_order(row.public_id)

    def complete(self, work_order_id: str, payload: CompleteWorkOrderRequest) -> WorkOrderDetail:
        if not payload.confirm:
            raise MaintenanceConflictError(
                "Completion requires explicit confirmation.",
                code="maintenance_completion_required",
            )
        if not payload.completion_summary.strip():
            raise MaintenanceConflictError(
                "A completion summary is required.",
                code="maintenance_completion_required",
            )
        row = self._lock_work_order(work_order_id)
        if row.status not in COMPLETE_STATUSES:
            self._conflict(row, action="complete")
        previous = row.status
        now = utc_now()
        row.status = WorkOrderStatus.completed.value
        row.completed_at = now
        row.completed_by = payload.actor_name
        row.completion_result = payload.completion_result.value
        row.completion_summary = payload.completion_summary
        row.updated_at = now
        self._append_event(
            row,
            event_type="work_completed",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status=row.status,
            note=payload.completion_summary,
            metadata={"completion_result": payload.completion_result.value},
        )
        if payload.completion_result.value not in UNCHANGED_ASSET_RESULTS:
            self._sync_asset_dates(row, completed_at=now)
        self._commit()
        return self.get_work_order(row.public_id)

    def cancel(self, work_order_id: str, payload: CancelWorkOrderRequest) -> WorkOrderDetail:
        if not payload.confirm:
            raise MaintenanceConflictError(
                "Cancellation requires a reason and explicit confirmation.",
                code="maintenance_cancellation_reason_required",
            )
        if not payload.reason.strip():
            raise MaintenanceConflictError(
                "A cancellation reason is required.",
                code="maintenance_cancellation_reason_required",
            )
        row = self._lock_work_order(work_order_id)
        if row.status not in CANCEL_STATUSES:
            self._conflict(row, action="cancel")
        previous = row.status
        now = utc_now()
        row.status = WorkOrderStatus.cancelled.value
        row.cancelled_at = now
        row.cancelled_by = payload.actor_name
        row.cancellation_reason = payload.reason
        row.updated_at = now
        self._append_event(
            row,
            event_type="work_cancelled",
            actor_name=payload.actor_name,
            from_status=previous,
            to_status=row.status,
            note=payload.reason,
        )
        self._commit()
        return self.get_work_order(row.public_id)

    def list_plans(self, *, asset_id: str | None = None, enabled: bool | None = None) -> MaintenancePlanListResponse:
        now = self.reference_time()
        try:
            rows = self.repository.list_plans(asset_id=asset_id, enabled=enabled)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        return MaintenancePlanListResponse(
            items=[self._to_plan(row) for row in rows],
            total=len(rows),
            reference_time=now,
        )

    def get_plan(self, plan_id: str) -> MaintenancePlanSummary:
        row = self._load_plan(plan_id)
        return self._to_plan(row)

    def create_plan(self, payload: CreatePlanRequest) -> MaintenancePlanSummary:
        asset = self._require_asset(payload.asset_id)
        row = MaintenancePlan(
            id=uuid4(),
            public_id=self.repository.next_plan_public_id(),
            asset_id=asset.id,
            name=payload.name,
            maintenance_type=payload.maintenance_type.value,
            interval_days=payload.interval_days,
            priority=payload.priority.value,
            instructions=payload.instructions,
            enabled=True,
            next_due_at=payload.next_due_at,
            created_by=payload.actor_name,
        )
        self.session.add(row)
        self.session.flush()
        self._append_plan_event(row, event_type="plan_created", actor_name=payload.actor_name)
        self._refresh_asset_next_maintenance(asset)
        self._commit()
        return self.get_plan(row.public_id)

    def update_plan(self, plan_id: str, payload: UpdatePlanRequest) -> MaintenancePlanSummary:
        row = self._lock_plan(plan_id)
        if payload.name is not None:
            row.name = payload.name
        if payload.interval_days is not None:
            row.interval_days = payload.interval_days
        if payload.priority is not None:
            row.priority = payload.priority.value
        if payload.instructions is not None:
            row.instructions = payload.instructions
        if payload.next_due_at is not None:
            row.next_due_at = payload.next_due_at
        if payload.enabled is not None:
            row.enabled = payload.enabled
        row.updated_at = utc_now()
        self._append_plan_event(row, event_type="plan_updated", actor_name=payload.actor_name)
        self.session.refresh(row, attribute_names=["asset"])
        self._refresh_asset_next_maintenance(row.asset)
        self._commit()
        return self.get_plan(row.public_id)

    def disable_plan(self, plan_id: str, payload: DisablePlanRequest) -> MaintenancePlanSummary:
        row = self._lock_plan(plan_id)
        row.enabled = False
        row.updated_at = utc_now()
        self._append_plan_event(
            row,
            event_type="plan_disabled",
            actor_name=payload.actor_name,
            note=payload.note,
        )
        self.session.refresh(row, attribute_names=["asset"])
        self._refresh_asset_next_maintenance(row.asset)
        self._commit()
        return self.get_plan(row.public_id)

    def asset_maintenance(self, asset_id: str) -> AssetMaintenanceResponse:
        now = self.reference_time()
        asset = self._require_asset(asset_id)
        try:
            plans = self.repository.enabled_plans_for_asset(asset.id)
            open_orders = self.repository.list_open_for_asset(asset.id)
            recent = self.repository.list_recent_completed_for_asset(asset.id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        overdue = any(is_overdue(item.due_at, item.status, now) for item in open_orders)
        return AssetMaintenanceResponse(
            asset_id=asset.external_id,
            overdue=overdue,
            last_maintenance_at=asset.last_maintenance_at,
            next_maintenance_at=asset.next_maintenance_at,
            active_plans=[self._to_plan(item) for item in plans],
            open_work_orders=[self._to_summary(item, now) for item in open_orders],
            recent_completed=[self._to_summary(item, now) for item in recent],
            reference_time=now,
        )

    def incident_maintenance(self, incident_id: str) -> IncidentMaintenanceResponse:
        now = self.reference_time()
        incident = self._optional_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError(incident_id.strip().upper())
        rows = self.repository.list_work_orders(
            incident_id=incident.incident_number,
            reference_time=now,
        )
        return IncidentMaintenanceResponse(
            incident_id=incident.incident_number,
            items=[self._to_summary(item, now) for item in rows],
            total=len(rows),
            reference_time=now,
        )

    def upcoming(self, *, limit: int = 12) -> list[UpcomingMaintenanceItem]:
        now = self.reference_time()
        rows = self.repository.list_upcoming(now, limit=limit)
        return [
            UpcomingMaintenanceItem(
                id=row.public_id,
                kind="work_order",
                title=row.title,
                asset_id=row.asset.external_id,
                asset_name=row.asset.name,
                zone=row.asset.zone.name if row.asset.zone is not None else "",
                due_at=row.due_at,
                priority=MaintenancePriority(row.priority),
                maintenance_type=MaintenanceType(row.maintenance_type),
                status=row.status,
                overdue=is_overdue(row.due_at, row.status, now),
            )
            for row in rows
        ]

    def generate_due_work_orders(self, *, as_of: datetime, actor_name: str = "Maintenance Generator") -> dict[str, int]:
        created = 0
        skipped = 0
        errors = 0
        try:
            plans = self.repository.list_enabled_due_plans(as_of)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        for plan in plans:
            try:
                with self.session.begin_nested():
                    if self.repository.has_open_work_order_for_plan(plan.id):
                        skipped += 1
                        continue
                    asset = plan.asset
                    row = MaintenanceWorkOrder(
                        id=uuid4(),
                        public_id=self.repository.next_work_order_public_id(),
                        asset_id=plan.asset_id,
                        maintenance_plan_id=plan.id,
                        maintenance_type=plan.maintenance_type,
                        title=f"{plan.name} · {asset.external_id}",
                        description=plan.instructions,
                        priority=plan.priority,
                        status=WorkOrderStatus.scheduled.value,
                        due_at=plan.next_due_at,
                        created_by=actor_name,
                    )
                    self.session.add(row)
                    self.session.flush()
                    self._append_event(
                        row,
                        event_type="work_order_created",
                        actor_name=actor_name,
                        from_status=None,
                        to_status=row.status,
                        note="Generated from enabled maintenance plan.",
                        plan=plan,
                        metadata={"generated": True, "as_of": as_of.isoformat()},
                    )
                    plan.last_generated_at = as_of
                    plan.next_due_at = plan.next_due_at + timedelta(days=plan.interval_days)
                    plan.updated_at = utc_now()
                    created += 1
            except (OperationalError, InterfaceError):
                self.session.rollback()
                raise DatabaseUnavailableError
            except Exception:
                errors += 1
        self._commit()
        return {"created": created, "skipped": skipped, "errors": errors, "examined": len(plans)}

    def _sync_asset_dates(self, row: MaintenanceWorkOrder, *, completed_at: datetime) -> None:
        asset = self.session.get(Asset, row.asset_id)
        if asset is None:
            return
        if row.completion_result in SUCCESSFUL_COMPLETION_RESULTS:
            asset.last_maintenance_at = completed_at
            self._refresh_asset_next_maintenance(asset)

    def _refresh_asset_next_maintenance(self, asset: Asset) -> None:
        plans = self.repository.enabled_plans_for_asset(asset.id)
        if plans:
            asset.next_maintenance_at = min(item.next_due_at for item in plans)

    def _append_event(
        self,
        row: MaintenanceWorkOrder,
        *,
        event_type: str,
        actor_name: str,
        from_status: str | None,
        to_status: str | None,
        note: str | None = None,
        plan: MaintenancePlan | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MaintenanceWorkOrderEvent:
        event = MaintenanceWorkOrderEvent(
            id=uuid4(),
            public_id=self.repository.next_event_public_id(),
            work_order_id=row.id,
            plan_id=plan.id if plan is not None else row.maintenance_plan_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_name=actor_name,
            note=note,
            extra_metadata=dict(metadata or {}),
            created_at=utc_now(),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _append_plan_event(
        self,
        plan: MaintenancePlan,
        *,
        event_type: str,
        actor_name: str,
        note: str | None = None,
    ) -> MaintenanceWorkOrderEvent:
        event = MaintenanceWorkOrderEvent(
            id=uuid4(),
            public_id=self.repository.next_event_public_id(),
            work_order_id=None,
            plan_id=plan.id,
            event_type=event_type,
            actor_name=actor_name,
            note=note,
            extra_metadata={},
            created_at=utc_now(),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _to_summary(self, row: MaintenanceWorkOrder, now: datetime) -> WorkOrderSummary:
        asset = row.asset
        zone = asset.zone
        return WorkOrderSummary(
            id=row.public_id,
            public_id=row.public_id,
            asset_id=asset.external_id,
            asset_name=asset.name,
            asset_type=AssetType(asset.asset_type),
            zone=zone.name if zone is not None else "",
            zone_id=public_zone_id(zone.code) if zone is not None else "",
            location_label=asset.location_label,
            has_cellular_identity=bool(asset.device_msisdn),
            device_msisdn_masked=mask_device_msisdn(asset.device_msisdn),
            maintenance_plan_id=row.plan.public_id if row.plan is not None else None,
            incident_id=row.incident.incident_number if row.incident is not None else None,
            maintenance_type=MaintenanceType(row.maintenance_type),
            title=row.title,
            description=row.description,
            instructions=row.plan.instructions if row.plan is not None else None,
            priority=MaintenancePriority(row.priority),
            status=WorkOrderStatus(row.status),
            assigned_to=row.assigned_to,
            scheduled_start_at=row.scheduled_start_at,
            due_at=row.due_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            completed_by=row.completed_by,
            cancelled_at=row.cancelled_at,
            cancelled_by=row.cancelled_by,
            cancellation_reason=row.cancellation_reason,
            completion_summary=row.completion_summary,
            completion_result=row.completion_result,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            overdue=is_overdue(row.due_at, row.status, now),
            allowed_actions=allowed_actions(row.status),
        )

    def _to_plan(self, row: MaintenancePlan) -> MaintenancePlanSummary:
        asset = row.asset
        return MaintenancePlanSummary(
            id=row.public_id,
            public_id=row.public_id,
            asset_id=asset.external_id,
            asset_name=asset.name,
            asset_type=AssetType(asset.asset_type),
            zone=asset.zone.name if asset.zone is not None else "",
            name=row.name,
            maintenance_type=MaintenanceType(row.maintenance_type),
            interval_days=row.interval_days,
            priority=MaintenancePriority(row.priority),
            instructions=row.instructions,
            enabled=row.enabled,
            last_generated_at=row.last_generated_at,
            next_due_at=row.next_due_at,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_event(self, event: MaintenanceWorkOrderEvent) -> WorkOrderHistoryEvent:
        return WorkOrderHistoryEvent(
            id=event.public_id,
            public_id=event.public_id,
            event_type=event.event_type,
            from_status=event.from_status,
            to_status=event.to_status,
            actor_name=event.actor_name,
            note=event.note,
            created_at=event.created_at,
        )

    def _load_work_order(self, work_order_id: str) -> MaintenanceWorkOrder:
        try:
            row = self.repository.get_work_order(work_order_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise MaintenanceWorkOrderNotFoundError(work_order_id)
        return row

    def _lock_work_order(self, work_order_id: str) -> MaintenanceWorkOrder:
        try:
            row = self.repository.get_work_order_for_update(work_order_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise MaintenanceWorkOrderNotFoundError(work_order_id)
        return row

    def _load_plan(self, plan_id: str) -> MaintenancePlan:
        try:
            row = self.repository.get_plan(plan_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise MaintenancePlanNotFoundError(plan_id)
        return row

    def _lock_plan(self, plan_id: str) -> MaintenancePlan:
        try:
            row = self.repository.get_plan_for_update(plan_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if row is None:
            raise MaintenancePlanNotFoundError(plan_id)
        return row

    def _require_asset(self, asset_id: str) -> Asset:
        try:
            asset = self.assets.get_by_external_id(asset_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if asset is None:
            raise AssetNotFoundError(asset_id)
        return asset

    def _optional_incident(self, incident_id: str | None) -> Incident | None:
        if not incident_id:
            return None
        try:
            incident = self.incidents.get_by_number(incident_id)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        if incident is None:
            raise IncidentNotFoundError(incident_id.strip().upper())
        return incident

    def _conflict(self, row: MaintenanceWorkOrder, *, action: str) -> None:
        if row.status in TERMINAL_STATUSES:
            raise MaintenanceConflictError(
                f"Work order {row.public_id} is already {row.status.replace('_', ' ')}.",
                code="invalid_maintenance_transition",
            )
        raise MaintenanceConflictError(
            f"Cannot {action.replace('_', ' ')} a work order with status '{row.status}'.",
            code="invalid_maintenance_transition",
        )

    def _commit(self) -> None:
        try:
            self.session.commit()
        except (OperationalError, InterfaceError) as exc:
            self.session.rollback()
            raise DatabaseUnavailableError from exc
        except Exception:
            self.session.rollback()
            raise
