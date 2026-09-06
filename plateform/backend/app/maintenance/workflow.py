"""Maintenance work-order transition table. No I/O.

Overdue is derived from due_at and is never stored as a status.
Completing a record does not execute a physical device command.
"""

ACTION_MAP: dict[str, tuple[str, ...]] = {
    "scheduled": ("assign", "reschedule", "add_note", "start", "cancel"),
    "assigned": ("assign", "reschedule", "add_note", "start", "cancel"),
    "in_progress": ("add_note", "complete", "cancel"),
    "completed": (),
    "cancelled": (),
}

STATUSES = ("scheduled", "assigned", "in_progress", "completed", "cancelled")
OPEN_STATUSES = {"scheduled", "assigned", "in_progress"}
TERMINAL_STATUSES = {"completed", "cancelled"}
ASSIGN_STATUSES = {"scheduled", "assigned"}
RESCHEDULE_STATUSES = {"scheduled", "assigned"}
START_STATUSES = {"scheduled", "assigned"}
NOTE_STATUSES = OPEN_STATUSES
COMPLETE_STATUSES = {"in_progress"}
CANCEL_STATUSES = OPEN_STATUSES

MAINTENANCE_TYPES = (
    "preventive",
    "inspection",
    "calibration",
    "battery_replacement",
    "connectivity_check",
    "corrective",
)
PRIORITIES = ("low", "medium", "high", "critical")
PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
COMPLETION_RESULTS = (
    "completed_successfully",
    "follow_up_required",
    "asset_repaired",
    "asset_replaced",
    "no_fault_found",
    "unable_to_complete",
    "other",
)
SUCCESSFUL_COMPLETION_RESULTS = {
    "completed_successfully",
    "asset_repaired",
    "asset_replaced",
    "no_fault_found",
    "other",
}
UNCHANGED_ASSET_RESULTS = {"follow_up_required", "unable_to_complete"}
EVENT_TYPES = (
    "work_order_created",
    "work_order_assigned",
    "work_order_rescheduled",
    "work_started",
    "note_added",
    "work_completed",
    "work_cancelled",
    "plan_created",
    "plan_updated",
    "plan_disabled",
)


def allowed_actions(status: str) -> list[str]:
    return list(ACTION_MAP.get(status, ()))


def is_overdue(due_at, status: str, reference_time) -> bool:
    return status not in TERMINAL_STATUSES and due_at is not None and due_at < reference_time
