from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.schemas.assets import AssetType
from app.schemas.incidents import ActorRequest, SortOrder, _trim_optional


class MaintenanceType(str, Enum):
    preventive = "preventive"
    inspection = "inspection"
    calibration = "calibration"
    battery_replacement = "battery_replacement"
    connectivity_check = "connectivity_check"
    corrective = "corrective"


class MaintenancePriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class WorkOrderStatus(str, Enum):
    scheduled = "scheduled"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class CompletionResult(str, Enum):
    completed_successfully = "completed_successfully"
    follow_up_required = "follow_up_required"
    asset_repaired = "asset_repaired"
    asset_replaced = "asset_replaced"
    no_fault_found = "no_fault_found"
    unable_to_complete = "unable_to_complete"
    other = "other"


class WorkOrderSortField(str, Enum):
    due_at = "due_at"
    priority = "priority"
    status = "status"
    created_at = "created_at"
    asset_name = "asset_name"


class MaintenanceEventType(str, Enum):
    work_order_created = "work_order_created"
    work_order_assigned = "work_order_assigned"
    work_order_rescheduled = "work_order_rescheduled"
    work_started = "work_started"
    note_added = "note_added"
    work_completed = "work_completed"
    work_cancelled = "work_cancelled"
    plan_created = "plan_created"
    plan_updated = "plan_updated"
    plan_disabled = "plan_disabled"


class CreateWorkOrderRequest(ActorRequest):
    asset_id: str = Field(..., min_length=1, max_length=80)
    maintenance_plan_id: str | None = Field(default=None, max_length=32)
    incident_id: str | None = Field(default=None, max_length=32)
    maintenance_type: MaintenanceType
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: MaintenancePriority = MaintenancePriority.medium
    assigned_to: str | None = Field(default=None, max_length=120)
    scheduled_start_at: datetime | None = None
    due_at: datetime

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("title is required")
        return trimmed

    @field_validator("description", "assigned_to", "maintenance_plan_id", "incident_id")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=4000)


class AssignWorkOrderRequest(ActorRequest):
    assigned_to: str = Field(..., min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("assigned_to")
    @classmethod
    def trim_assignee(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("assigned_to is required")
        return trimmed

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class RescheduleWorkOrderRequest(ActorRequest):
    due_at: datetime
    scheduled_start_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class StartWorkOrderRequest(ActorRequest):
    assigned_to: str | None = Field(default=None, max_length=120)
    confirm_unassigned: bool = False
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("assigned_to", "note")
    @classmethod
    def trim_optional_fields(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=2000)


class MaintenanceNoteRequest(ActorRequest):
    note: str = Field(..., min_length=1, max_length=2000)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("note is required")
        return trimmed


class CompleteWorkOrderRequest(ActorRequest):
    completion_result: CompletionResult
    completion_summary: str = Field(..., min_length=1, max_length=2000)
    confirm: bool = False

    @field_validator("completion_summary")
    @classmethod
    def trim_summary(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("completion_summary is required")
        return trimmed


class CancelWorkOrderRequest(ActorRequest):
    reason: str = Field(..., min_length=1, max_length=2000)
    confirm: bool = False

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("reason is required")
        return trimmed


class CreatePlanRequest(ActorRequest):
    asset_id: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=200)
    maintenance_type: MaintenanceType
    interval_days: int = Field(..., gt=0)
    priority: MaintenancePriority = MaintenancePriority.medium
    instructions: str | None = Field(default=None, max_length=4000)
    next_due_at: datetime

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name is required")
        return trimmed

    @field_validator("instructions")
    @classmethod
    def trim_instructions(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=4000)


class UpdatePlanRequest(ActorRequest):
    name: str | None = Field(default=None, max_length=200)
    interval_days: int | None = Field(default=None, gt=0)
    priority: MaintenancePriority | None = None
    instructions: str | None = Field(default=None, max_length=4000)
    next_due_at: datetime | None = None
    enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=200)

    @field_validator("instructions")
    @classmethod
    def trim_instructions(cls, value: str | None) -> str | None:
        return _trim_optional(value, maximum=4000)


class DisablePlanRequest(ActorRequest):
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class MaintenancePlanSummary(BaseModel):
    id: str
    public_id: str
    asset_id: str
    asset_name: str
    asset_type: AssetType
    zone: str
    name: str
    maintenance_type: MaintenanceType
    interval_days: int
    priority: MaintenancePriority
    instructions: str | None = None
    enabled: bool
    last_generated_at: datetime | None = None
    next_due_at: datetime
    created_by: str
    created_at: datetime
    updated_at: datetime


class MaintenancePlanListResponse(BaseModel):
    items: list[MaintenancePlanSummary]
    total: int
    reference_time: datetime


class WorkOrderSummary(BaseModel):
    id: str
    public_id: str
    asset_id: str
    asset_name: str
    asset_type: AssetType
    zone: str
    zone_id: str
    location_label: str | None = None
    has_cellular_identity: bool = False
    device_msisdn_masked: str | None = None
    maintenance_plan_id: str | None = None
    incident_id: str | None = None
    maintenance_type: MaintenanceType
    title: str
    description: str | None = None
    instructions: str | None = None
    priority: MaintenancePriority
    status: WorkOrderStatus
    assigned_to: str | None = None
    scheduled_start_at: datetime | None = None
    due_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    completion_summary: str | None = None
    completion_result: CompletionResult | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    overdue: bool
    allowed_actions: list[str]


class WorkOrderHistoryEvent(BaseModel):
    id: str
    public_id: str
    event_type: MaintenanceEventType
    from_status: WorkOrderStatus | None = None
    to_status: WorkOrderStatus | None = None
    actor_name: str
    note: str | None = None
    created_at: datetime


class WorkOrderDetail(WorkOrderSummary):
    history: list[WorkOrderHistoryEvent] = Field(default_factory=list)


class WorkOrderHistoryResponse(BaseModel):
    work_order_id: str
    items: list[WorkOrderHistoryEvent]
    total: int


class MaintenanceSummary(BaseModel):
    overdue: int
    due_within_7_days: int
    in_progress: int
    completed_in_period: int
    critical: int
    assets_without_plan: int
    open_work_orders: int
    reference_time: datetime


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderSummary]
    total: int
    summary: MaintenanceSummary
    reference_time: datetime


class UpcomingMaintenanceItem(BaseModel):
    id: str
    kind: str
    title: str
    asset_id: str
    asset_name: str
    zone: str
    due_at: datetime
    priority: MaintenancePriority
    maintenance_type: MaintenanceType
    status: str | None = None
    overdue: bool = False


class AssetMaintenanceResponse(BaseModel):
    asset_id: str
    overdue: bool
    last_maintenance_at: datetime | None = None
    next_maintenance_at: datetime | None = None
    active_plans: list[MaintenancePlanSummary]
    open_work_orders: list[WorkOrderSummary]
    recent_completed: list[WorkOrderSummary]
    reference_time: datetime


class IncidentMaintenanceResponse(BaseModel):
    incident_id: str
    items: list[WorkOrderSummary]
    total: int
    reference_time: datetime
