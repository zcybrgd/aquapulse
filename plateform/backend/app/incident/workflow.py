"""Incident operations transition table. No I/O.

Current incident statuses are investigating, awaiting_approval, and resolved.
Acknowledgement, response start, and false-alarm are metadata or resolution
codes, not statuses.
"""

from __future__ import annotations

from typing import Any

LEGACY_INCIDENT_STATUS_MAP = {
    "open": "investigating",
    "acknowledged": "investigating",
    "investigating": "investigating",
    "responding": "investigating",
    "monitoring": "investigating",
    "awaiting_approval": "awaiting_approval",
    "resolved": "resolved",
    "false_alarm": "resolved",
}

ACTION_MAP: dict[str, tuple[str, ...]] = {
    "investigating": (
        "acknowledge",
        "assign",
        "add_note",
        "request_approval",
        "start_response",
        "resolve",
        "false_alarm",
    ),
    "awaiting_approval": (
        "assign",
        "add_note",
        "start_investigation",
        "return_investigation",
        "start_response",
        "resolve",
        "false_alarm",
    ),
    "resolved": ("reopen",),
}

ACTIVE_STATUSES = {"investigating", "awaiting_approval"}
TERMINAL_STATUSES = {"resolved"}
NOTE_STATUSES = ACTIVE_STATUSES
ASSIGN_STATUSES = ACTIVE_STATUSES
ACKNOWLEDGE_STATUSES = {"investigating"}
START_INVESTIGATION_STATUSES = {"investigating", "awaiting_approval"}
RETURN_INVESTIGATION_STATUSES = {"awaiting_approval"}
REQUEST_APPROVAL_STATUSES = {"investigating"}
START_RESPONSE_STATUSES = ACTIVE_STATUSES
RESOLVE_STATUSES = ACTIVE_STATUSES
FALSE_ALARM_STATUSES = ACTIVE_STATUSES
REOPEN_STATUSES = TERMINAL_STATUSES

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


def can_manage_tasks(incident: Any) -> bool:
    return incident.status == "investigating" and incident.response_started_at is not None


def migrate_incident_status(status: str) -> str:
    return LEGACY_INCIDENT_STATUS_MAP.get(status, status)
