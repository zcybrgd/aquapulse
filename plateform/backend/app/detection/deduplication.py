"""Deduplication and correlation for deterministic detections.

Correlation key: `{sensor_external_id}:{rule_code}:{condition}`.

Cooldown / open-condition behaviour:

* While an active detection (`new`, `queued`, `under_review`) for the same
  sensor and rule has `condition_open=true`, another identical detection is
  not created. `repeat_count` in evidence_summary is incremented instead.
* When a later run does not trigger the rule, `condition_open` is set to
  false (recovery). The original detection stays in the queue for operators.
* After recovery, a new occurrence creates a new detection even if it falls
  inside the configured cooldown window.
* Different rules may each create a detection for the same sensor/window.
* Combined rules may list related PRESSURE_DROP / FLOW_SURGE detection numbers.

Cooldown minutes come from the rule `configuration` (default 60).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.detection import AnomalyDetection

ACTIVE_STATUSES = ("new", "queued", "under_review")


def correlation_key(sensor_external_id: str, rule_code: str, condition: str) -> str:
    return f"{sensor_external_id}:{rule_code}:{condition}"


def condition_token(rule_code: str) -> str:
    if rule_code == "MISSING_TELEMETRY":
        return "outage"
    if rule_code == "SENSOR_QUALITY":
        return "quality"
    if rule_code == "CONNECTIVITY_DEGRADATION":
        return "connectivity"
    return "active"


def find_open_detection(
    session: Session,
    *,
    sensor_id,
    rule_id,
    correlation_key_value: str,
) -> AnomalyDetection | None:
    return session.scalar(
        select(AnomalyDetection)
        .where(
            AnomalyDetection.sensor_id == sensor_id,
            AnomalyDetection.rule_id == rule_id,
            AnomalyDetection.correlation_key == correlation_key_value,
            AnomalyDetection.status.in_(ACTIVE_STATUSES),
        )
        .order_by(AnomalyDetection.detected_at.desc())
        .limit(1)
    )


def is_still_open(detection: AnomalyDetection) -> bool:
    summary = detection.evidence_summary or {}
    return bool(summary.get("condition_open", True))


def mark_recovered(detection: AnomalyDetection, *, now: datetime) -> None:
    summary = dict(detection.evidence_summary or {})
    summary["condition_open"] = False
    summary["recovered_at"] = now.isoformat()
    detection.evidence_summary = summary
    flag_modified(detection, "evidence_summary")
    detection.updated_at = now


def record_repeat(detection: AnomalyDetection, *, now: datetime, window_end: datetime) -> int:
    summary = dict(detection.evidence_summary or {})
    count = int(summary.get("repeat_count", 1)) + 1
    summary["repeat_count"] = count
    summary["condition_open"] = True
    summary["last_seen_at"] = now.isoformat()
    summary["window_end"] = window_end.isoformat()
    detection.evidence_summary = summary
    flag_modified(detection, "evidence_summary")
    detection.updated_at = now
    return count


def cooldown_minutes(configuration: dict[str, Any] | None, default: int = 60) -> int:
    if not configuration:
        return default
    value = configuration.get("cooldown_minutes", default)
    return max(1, int(value))


def within_cooldown(detection: AnomalyDetection, *, now: datetime, minutes: int) -> bool:
    return detection.detected_at >= now - timedelta(minutes=minutes)
