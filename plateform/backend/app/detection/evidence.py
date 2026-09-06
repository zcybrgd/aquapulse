"""Structured evidence builders for stored detections."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.base import utc_now
from app.db.models.detection import DetectionEvidence
from app.detection.rules import EvidenceItem, RuleHit


def build_evidence_summary(
    hit: RuleHit,
    *,
    score_explanation: dict[str, Any],
    rule_code: str,
    rule_version: int,
    related_detection_numbers: list[str],
    repeat_count: int = 1,
    condition_open: bool = True,
) -> dict[str, Any]:
    return {
        "rule_code": rule_code,
        "rule_version": rule_version,
        "window_start": hit.window_start.astimezone(timezone.utc).isoformat(),
        "window_end": hit.window_end.astimezone(timezone.utc).isoformat(),
        "reading_count": hit.reading_count,
        "reason_codes": hit.reason_codes,
        "score": score_explanation,
        "related_detection_numbers": related_detection_numbers,
        "repeat_count": repeat_count,
        "condition_open": condition_open,
        "items": [
            {
                "metric": item.metric,
                "observed_value": item.observed_value,
                "baseline_value": item.baseline_value,
                "threshold_value": item.threshold_value,
                "unit": item.unit,
                "evidence_type": item.evidence_type,
                "details": item.details,
            }
            for item in hit.evidence
        ],
        "timescale_window": {
            "start": hit.window_start.astimezone(timezone.utc).isoformat(),
            "end": hit.window_end.astimezone(timezone.utc).isoformat(),
            "note": "Raw readings remain in sensor_readings; this table stores the summary only.",
        },
    }


def evidence_rows(detection_id, hit: RuleHit, *, created_at: datetime | None = None) -> list[DetectionEvidence]:
    stamp = created_at or utc_now()
    rows: list[DetectionEvidence] = []
    for item in hit.evidence:
        rows.append(
            DetectionEvidence(
                id=uuid4(),
                detection_id=detection_id,
                metric=item.metric,
                observed_value=item.observed_value,
                baseline_value=item.baseline_value,
                threshold_value=item.threshold_value,
                unit=item.unit,
                evidence_type=item.evidence_type,
                reading_start_time=hit.window_start,
                reading_end_time=hit.window_end,
                details=item.details,
                created_at=stamp,
            )
        )
    return rows
