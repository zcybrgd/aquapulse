"""Deterministic detection engine. No LLM, no random scoring, no unbounded queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.base import utc_now
from app.db.models import Asset, DetectionRule, Organization
from app.db.models.detection import AnomalyDetection
from app.detection.catalog import MAX_QUERY_WINDOW_MINUTES, MAX_READINGS_PER_SENSOR
from app.detection.deduplication import (
    condition_token,
    correlation_key,
    find_open_detection,
    is_still_open,
    mark_recovered,
    record_repeat,
)
from app.detection.evidence import build_evidence_summary, evidence_rows
from app.detection.rules import (
    ReadingPoint,
    RuleHit,
    evaluate_combined_leak_pattern,
    evaluate_connectivity,
    evaluate_flow_surge,
    evaluate_missing_telemetry,
    evaluate_pressure_drop,
    evaluate_sensor_quality,
)
from app.detection.scoring import priority_for_score, score_components
from app.repositories.detections import DetectionRepository
from app.repositories.telemetry import TelemetryRepository
from app.services.telemetry_constants import DATA_MODE


@dataclass
class DetectionCandidate:
    sensor: Asset
    rule: DetectionRule
    hit: RuleHit
    score_explanation: dict[str, Any]
    correlation: str
    related_detection_numbers: list[str] = field(default_factory=list)


@dataclass
class DetectionRunSummary:
    sensors_checked: int = 0
    rules_evaluated: int = 0
    detections_created: int = 0
    detections_deduplicated: int = 0
    recovered: int = 0
    errors: int = 0
    dry_run: bool = False
    created_numbers: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    finished_at: datetime | None = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _points_from_readings(rows) -> list[ReadingPoint]:
    return [
        ReadingPoint(
            time=_as_utc(row.time),
            pressure_kpa=row.pressure_kpa,
            flow_lps=row.flow_lps,
            temperature_c=row.temperature_c,
            signal_strength_dbm=row.signal_strength_dbm,
            packet_loss_pct=row.packet_loss_pct,
            battery_pct=row.battery_pct,
        )
        for row in rows
    ]


def evaluate_rule(
    rule: DetectionRule,
    *,
    readings: list[ReadingPoint],
    latest: datetime | None,
    has_prior: bool,
    now: datetime,
    sampling_interval_seconds: int | None,
    metadata: dict[str, Any] | None,
    window_start: datetime,
    window_end: datetime,
) -> RuleHit:
    config = rule.configuration or {}
    if rule.code == "PRESSURE_DROP":
        return evaluate_pressure_drop(
            readings,
            threshold_pct=rule.threshold,
            minimum_points=rule.minimum_points,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.code == "FLOW_SURGE":
        return evaluate_flow_surge(
            readings,
            threshold_pct=rule.threshold,
            minimum_points=rule.minimum_points,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.code == "COMBINED_LEAK_PATTERN":
        return evaluate_combined_leak_pattern(
            readings,
            pressure_drop_pct=float(config.get("pressure_drop_pct", rule.threshold)),
            flow_surge_pct=float(config.get("flow_surge_pct", rule.secondary_threshold or 0)),
            minimum_points=rule.minimum_points,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.code == "CONNECTIVITY_DEGRADATION":
        return evaluate_connectivity(
            readings,
            packet_loss_threshold=float(config.get("packet_loss_pct", rule.threshold)),
            signal_threshold_dbm=float(config.get("signal_strength_dbm", rule.secondary_threshold or 0)),
            intermittent_gap_minutes=float(config.get("intermittent_gap_minutes", 15)),
            minimum_points=rule.minimum_points,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.code == "MISSING_TELEMETRY":
        return evaluate_missing_telemetry(
            latest=latest,
            has_prior_readings=has_prior,
            freshness_minutes=float(config.get("freshness_minutes", rule.threshold)),
            now=now,
            require_prior=bool(config.get("require_prior_readings", True)),
        )
    if rule.code == "SENSOR_QUALITY":
        return evaluate_sensor_quality(
            readings,
            metadata=metadata,
            fallback_ranges=config.get("fallback_ranges") or {},
            frozen_minutes=float(config.get("frozen_minutes", 15)),
            frozen_minimum_points=int(config.get("frozen_minimum_points", 5)),
            inconsistent_ratio_max=float(config.get("inconsistent_pressure_flow_ratio_max", 50)),
            minimum_points=rule.minimum_points,
            window_start=window_start,
            window_end=window_end,
            use_sensor_ranges=bool(config.get("use_sensor_valid_ranges", True)),
        )
    return RuleHit(
        triggered=False,
        reason_codes=[],
        trigger_reason="",
        evidence=[],
        observed_ratio=0.0,
        metric_count=0,
        window_start=window_start,
        window_end=window_end,
        reading_count=len(readings),
    )


class DetectionEngine:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DetectionRepository(session)
        self.telemetry = TelemetryRepository(session)

    def run(
        self,
        *,
        sensor_external_id: str | None = None,
        rule_code: str | None = None,
        window_minutes: int | None = None,
        dry_run: bool = False,
        explain: bool = False,
        now: datetime | None = None,
        persist_run_stats: bool = True,
    ) -> DetectionRunSummary:
        clock = _as_utc(now or utc_now())
        summary = DetectionRunSummary(dry_run=dry_run)
        organization = self.repository.get_organization()
        rules = self.repository.list_enabled_rules(code=rule_code)
        sensors = self.repository.list_sensors(external_id=sensor_external_id)
        summary.sensors_checked = len(sensors)

        lookback = window_minutes or max((rule.window_minutes for rule in rules), default=30)
        lookback = min(max(lookback, 1), MAX_QUERY_WINDOW_MINUTES)
        window_start = clock - timedelta(minutes=lookback)

        created_this_run: dict[tuple[str, str], str] = {}

        for sensor in sensors:
            try:
                rows = self.telemetry.history_raw(
                    sensor_id=sensor.id,
                    start=window_start,
                    end=clock,
                    limit=MAX_READINGS_PER_SENSOR,
                    metrics=["pressure", "flow", "temperature", "signal", "packet_loss", "battery"],
                )
                readings = _points_from_readings(rows)
                latest_row = self.telemetry.latest_for_sensor(sensor.id)
                latest_time = _as_utc(latest_row.time) if latest_row is not None else None
                has_prior = latest_row is not None or self.telemetry.has_readings(sensor.id)
                packet_loss = latest_row.packet_loss_pct if latest_row is not None else None
                criticality = sensor.pipeline_segment.criticality_score if sensor.pipeline_segment else None
                metadata = sensor.extra_metadata or {}

                for rule in rules:
                    summary.rules_evaluated += 1
                    hit = evaluate_rule(
                        rule,
                        readings=readings,
                        latest=latest_time,
                        has_prior=has_prior,
                        now=clock,
                        sampling_interval_seconds=sensor.sampling_interval_seconds,
                        metadata=metadata,
                        window_start=window_start,
                        window_end=clock,
                    )
                    key = correlation_key(sensor.external_id, rule.code, condition_token(rule.code))
                    open_row = find_open_detection(
                        self.session,
                        sensor_id=sensor.id,
                        rule_id=rule.id,
                        correlation_key_value=key,
                    )

                    if not hit.triggered:
                        if open_row is not None and is_still_open(open_row) and not dry_run:
                            mark_recovered(open_row, now=clock)
                            summary.recovered += 1
                        continue

                    if explain:
                        summary.explanations.append(
                            f"{sensor.external_id} {rule.code}: {hit.trigger_reason}"
                        )

                    if open_row is not None and is_still_open(open_row):
                        summary.detections_deduplicated += 1
                        if not dry_run:
                            record_repeat(open_row, now=clock, window_end=hit.window_end)
                        continue

                    related = self._related_numbers(sensor, rule, hit, created_this_run)
                    explanation = score_components(
                        severity_weight=rule.severity_weight,
                        observed_ratio=hit.observed_ratio,
                        threshold=self._score_threshold(rule),
                        metric_count=hit.metric_count,
                        criticality_score=criticality,
                        packet_loss_pct=packet_loss,
                        health_score=sensor.health_score,
                    )
                    candidate = DetectionCandidate(
                        sensor=sensor,
                        rule=rule,
                        hit=hit,
                        score_explanation=explanation,
                        correlation=key,
                        related_detection_numbers=related,
                    )
                    if dry_run:
                        summary.detections_created += 1
                        summary.created_numbers.append(f"DRY-{rule.code}-{sensor.external_id}")
                        continue
                    number = self._persist(organization, candidate, clock)
                    created_this_run[(sensor.external_id, rule.code)] = number
                    summary.detections_created += 1
                    summary.created_numbers.append(number)
            except Exception as exc:  # noqa: BLE001 — run must continue across sensors
                summary.errors += 1
                summary.error_messages.append(f"{sensor.external_id}: {exc.__class__.__name__}")

        summary.finished_at = clock
        if persist_run_stats and not dry_run and organization is not None:
            settings = dict(organization.settings or {})
            settings["seed_version"] = settings.get("seed_version", "step-7")
            settings["last_detection_run"] = {
                "finished_at": clock.isoformat(),
                "sensors_checked": summary.sensors_checked,
                "rules_evaluated": summary.rules_evaluated,
                "created": summary.detections_created,
                "deduplicated": summary.detections_deduplicated,
                "errors": summary.errors,
            }
            organization.settings = settings
            flag_modified(organization, "settings")
        if not dry_run:
            self.session.commit()
        return summary

    def _score_threshold(self, rule: DetectionRule) -> float:
        config = rule.configuration or {}
        if rule.code == "COMBINED_LEAK_PATTERN":
            return float(config.get("pressure_drop_pct", rule.threshold))
        if rule.code == "MISSING_TELEMETRY":
            return float(config.get("freshness_minutes", rule.threshold))
        if rule.code == "CONNECTIVITY_DEGRADATION":
            return float(config.get("packet_loss_pct", rule.threshold))
        if rule.code == "SENSOR_QUALITY":
            return float(config.get("frozen_minutes", rule.threshold))
        return float(rule.threshold)

    def _related_numbers(
        self,
        sensor: Asset,
        rule: DetectionRule,
        hit: RuleHit,
        created_this_run: dict[tuple[str, str], str],
    ) -> list[str]:
        related_codes = list((rule.configuration or {}).get("related_rule_codes") or [])
        numbers: list[str] = []
        for code in related_codes:
            created = created_this_run.get((sensor.external_id, code))
            if created:
                numbers.append(created)
        existing = self.repository.related_for_sensor_window(
            sensor_id=sensor.id,
            window_start=hit.window_start,
            window_end=hit.window_end,
            exclude_rule_id=rule.id,
        )
        for row in existing:
            if row.detection_number not in numbers:
                numbers.append(row.detection_number)
        return numbers

    def _persist(
        self,
        organization: Organization | None,
        candidate: DetectionCandidate,
        clock: datetime,
    ) -> str:
        if organization is None:
            raise RuntimeError("Organization is required to persist detections.")
        number = self.repository.next_detection_number(organization.id)
        score = float(candidate.score_explanation["anomaly_score"])
        detection_id = uuid4()
        summary = build_evidence_summary(
            candidate.hit,
            score_explanation=candidate.score_explanation,
            rule_code=candidate.rule.code,
            rule_version=candidate.rule.version,
            related_detection_numbers=candidate.related_detection_numbers,
        )
        row = AnomalyDetection(
            id=detection_id,
            detection_number=number,
            organization_id=organization.id,
            sensor_id=candidate.sensor.id,
            pipeline_segment_id=candidate.sensor.pipeline_segment_id,
            rule_id=candidate.rule.id,
            rule_version=candidate.rule.version,
            detected_at=clock,
            window_start=candidate.hit.window_start,
            window_end=candidate.hit.window_end,
            anomaly_score=score,
            priority=priority_for_score(score),
            status="new",
            trigger_reason=candidate.hit.trigger_reason[:500],
            reason_codes=candidate.hit.reason_codes,
            evidence_summary=summary,
            reading_count=candidate.hit.reading_count,
            correlation_key=candidate.correlation,
            incident_id=None,
            data_mode=DATA_MODE,
        )
        self.session.add(row)
        for item in evidence_rows(detection_id, candidate.hit, created_at=clock):
            self.session.add(item)
        self.session.flush()
        return number
