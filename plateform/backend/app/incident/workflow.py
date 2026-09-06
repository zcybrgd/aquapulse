"""Incident operations transition table. No I/O.

Legacy `monitoring` remains a valid active status so seeded incidents are not
forced into a new value. `acknowledged` is the Step 9 insertion between
`open` and `investigating`.
"""

ACTION_MAP: dict[str, tuple[str, ...]] = {
    "open": ("acknowledge", "assign", "add_note"),
    "acknowledged": ("assign", "start_investigation", "add_note"),
    "investigating": (
        "assign",
        "add_note",
        "request_approval",
        "start_response",
        "resolve",
        "false_alarm",
    ),
    "awaiting_approval": ("assign", "add_note", "start_response", "return_investigation"),
    "responding": ("assign", "add_note", "manage_tasks", "resolve"),
    "monitoring": ("assign", "add_note", "start_response", "resolve", "false_alarm"),
    "resolved": ("reopen",),
    "false_alarm": ("reopen",),
}

ACTIVE_STATUSES = {
    "open",
    "acknowledged",
    "investigating",
    "awaiting_approval",
    "responding",
    "monitoring",
}
TERMINAL_STATUSES = {"resolved", "false_alarm"}
NOTE_STATUSES = ACTIVE_STATUSES
ASSIGN_STATUSES = ACTIVE_STATUSES
ACKNOWLEDGE_STATUSES = {"open"}
START_INVESTIGATION_STATUSES = {"acknowledged"}
RETURN_INVESTIGATION_STATUSES = {"awaiting_approval"}
REQUEST_APPROVAL_STATUSES = {"investigating"}
START_RESPONSE_STATUSES = {"investigating", "awaiting_approval", "monitoring"}
RESOLVE_STATUSES = {"investigating", "responding", "monitoring"}
FALSE_ALARM_STATUSES = {"investigating", "monitoring"}
REOPEN_STATUSES = TERMINAL_STATUSES
TASK_MANAGE_STATUSES = {"responding"}

RESOLUTION_CODES = (
    "leak_repaired",
    "isolated_for_maintenance",
    "sensor_fault",
    "planned_operation",
    "false_alarm",
    "monitoring_completed",
    "other",
)

TASK_STATUSES = ("todo", "in_progress", "completed", "cancelled")
TASK_PRIORITIES = ("low", "medium", "high", "critical")
OPEN_TASK_STATUSES = {"todo", "in_progress"}


def allowed_actions(status: str) -> list[str]:
    return list(ACTION_MAP.get(status, ()))
