"""Transparent deterministic scoring. Weights are documented here only.

Final anomaly_score is clamped to [0, 1]. Priority is derived from that score
and is not mapped to incident Tier 1/2/3 in this step.
"""

from __future__ import annotations

from typing import Any

# Component weights must sum to 1.0.
SCORE_WEIGHTS: dict[str, float] = {
    "rule_severity": 0.40,
    "magnitude": 0.25,
    "corroboration": 0.15,
    "pipeline_criticality": 0.10,
    "telemetry_quality": 0.05,
    "asset_health": 0.05,
}

# Inclusive lower bound for each priority band.
PRIORITY_THRESHOLDS: dict[str, float] = {
    "low": 0.00,
    "medium": 0.35,
    "high": 0.55,
    "critical": 0.80,
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def magnitude_beyond_threshold(*, observed_ratio: float, threshold: float) -> float:
    """How far the observation exceeds the threshold, mapped to [0, 1].

    At the threshold the magnitude factor is 0. At twice the threshold it is 1.
    """
    if threshold <= 0:
        return 1.0 if observed_ratio > 0 else 0.0
    excess = max(0.0, observed_ratio - threshold)
    return _clamp(excess / threshold)


def corroboration_factor(metric_count: int) -> float:
    """One metric → 0; two → 0.5; three or more → 1.0."""
    if metric_count <= 1:
        return 0.0
    return _clamp((metric_count - 1) / 2.0)


def criticality_factor(criticality_score: int | None) -> float:
    """Pipeline criticality 1/2/3 maps to 1/3, 2/3, 1."""
    if criticality_score is None:
        return 0.0
    return _clamp(criticality_score / 3.0)


def telemetry_quality_factor(packet_loss_pct: float | None) -> float:
    """Higher packet loss increases the factor. 0% → 0, 20%+ → 1."""
    if packet_loss_pct is None:
        return 0.0
    return _clamp(packet_loss_pct / 20.0)


def asset_health_factor(health_score: float | None) -> float:
    """Lower asset health increases the factor. 100 → 0, 0 → 1."""
    if health_score is None:
        return 0.0
    return _clamp((100.0 - health_score) / 100.0)


def score_components(
    *,
    severity_weight: float,
    observed_ratio: float,
    threshold: float,
    metric_count: int,
    criticality_score: int | None,
    packet_loss_pct: float | None,
    health_score: float | None,
) -> dict[str, Any]:
    magnitude = magnitude_beyond_threshold(observed_ratio=observed_ratio, threshold=threshold)
    corroboration = corroboration_factor(metric_count)
    criticality = criticality_factor(criticality_score)
    quality = telemetry_quality_factor(packet_loss_pct)
    health = asset_health_factor(health_score)
    severity = _clamp(severity_weight)

    weighted = {
        "rule_severity": round(severity * SCORE_WEIGHTS["rule_severity"], 6),
        "magnitude": round(magnitude * SCORE_WEIGHTS["magnitude"], 6),
        "corroboration": round(corroboration * SCORE_WEIGHTS["corroboration"], 6),
        "pipeline_criticality": round(criticality * SCORE_WEIGHTS["pipeline_criticality"], 6),
        "telemetry_quality": round(quality * SCORE_WEIGHTS["telemetry_quality"], 6),
        "asset_health": round(health * SCORE_WEIGHTS["asset_health"], 6),
    }
    total = _clamp(sum(weighted.values()))
    return {
        "weights": SCORE_WEIGHTS,
        "factors": {
            "rule_severity": round(severity, 6),
            "magnitude": round(magnitude, 6),
            "corroboration": round(corroboration, 6),
            "pipeline_criticality": round(criticality, 6),
            "telemetry_quality": round(quality, 6),
            "asset_health": round(health, 6),
        },
        "weighted": weighted,
        "anomaly_score": round(total, 4),
    }


def priority_for_score(score: float) -> str:
    clamped = _clamp(score)
    if clamped >= PRIORITY_THRESHOLDS["critical"]:
        return "critical"
    if clamped >= PRIORITY_THRESHOLDS["high"]:
        return "high"
    if clamped >= PRIORITY_THRESHOLDS["medium"]:
        return "medium"
    return "low"
