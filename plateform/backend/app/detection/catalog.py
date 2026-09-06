"""Versioned deterministic detection rules.

Thresholds below are engineering demo values for the AquaPulse prototype.
They are not calibrated against field telemetry and must not be treated as a
leak confirmation or as machine-learning / AI output.
"""

from __future__ import annotations

from typing import Any

# Cooldown: if the same sensor+rule condition is still open, do not create
# another detection until the condition clears (recovery) and then recurs.
# See app.detection.deduplication.
DEFAULT_COOLDOWN_MINUTES = 60

# Bounded TimescaleDB lookback used by the engine (never unbounded).
MAX_QUERY_WINDOW_MINUTES = 360
MAX_READINGS_PER_SENSOR = 500

RULE_CATALOG: list[dict[str, Any]] = [
    {
        "code": "PRESSURE_DROP",
        "name": "Rapid pressure drop",
        "description": (
            "Pressure falls by at least the configured percentage within the "
            "evaluation window. Demo threshold — calibrate with field data."
        ),
        "rule_type": "rate_of_change",
        "metric": "pressure_kpa",
        "operator": "decrease_pct",
        "threshold": 8.0,
        "secondary_threshold": None,
        "window_minutes": 30,
        "minimum_points": 4,
        "severity_weight": 0.65,
        "enabled": True,
        "version": 1,
        "configuration": {
            "cooldown_minutes": DEFAULT_COOLDOWN_MINUTES,
            "comparison": "percent",
            "direction": "decrease",
            "demo_threshold": True,
        },
    },
    {
        "code": "FLOW_SURGE",
        "name": "Rapid flow surge",
        "description": (
            "Flow rises by at least the configured percentage within the "
            "evaluation window. Demo threshold — calibrate with field data."
        ),
        "rule_type": "rate_of_change",
        "metric": "flow_lps",
        "operator": "increase_pct",
        "threshold": 12.0,
        "secondary_threshold": None,
        "window_minutes": 30,
        "minimum_points": 4,
        "severity_weight": 0.60,
        "enabled": True,
        "version": 1,
        "configuration": {
            "cooldown_minutes": DEFAULT_COOLDOWN_MINUTES,
            "comparison": "percent",
            "direction": "increase",
            "demo_threshold": True,
        },
    },
    {
        "code": "COMBINED_LEAK_PATTERN",
        "name": "Combined pressure drop and flow surge",
        "description": (
            "Pressure decreases and flow increases in the same window. This is a "
            "suspicious pattern for investigation, not a confirmed leak."
        ),
        "rule_type": "cross_metric",
        "metric": "pressure_and_flow",
        "operator": "and",
        "threshold": 8.0,
        "secondary_threshold": 12.0,
        "window_minutes": 30,
        "minimum_points": 4,
        "severity_weight": 0.90,
        "enabled": True,
        "version": 1,
        "configuration": {
            "cooldown_minutes": DEFAULT_COOLDOWN_MINUTES,
            "pressure_drop_pct": 8.0,
            "flow_surge_pct": 12.0,
            "reason_code": "combined_pressure_drop_and_flow_surge",
            "related_rule_codes": ["PRESSURE_DROP", "FLOW_SURGE"],
            "demo_threshold": True,
        },
    },
    {
        "code": "CONNECTIVITY_DEGRADATION",
        "name": "Connectivity degradation",
        "description": (
            "Packet loss exceeds the threshold, signal strength is below the "
            "threshold, or measurements become intermittent. Demo thresholds."
        ),
        "rule_type": "connectivity",
        "metric": "connectivity",
        "operator": "any",
        "threshold": 10.0,
        "secondary_threshold": -100.0,
        "window_minutes": 30,
        "minimum_points": 3,
        "severity_weight": 0.55,
        "enabled": True,
        "version": 1,
        "configuration": {
            "cooldown_minutes": DEFAULT_COOLDOWN_MINUTES,
            "packet_loss_pct": 10.0,
            "signal_strength_dbm": -100.0,
            "intermittent_gap_minutes": 15.0,
            "demo_threshold": True,
        },
    },
    {
        "code": "MISSING_TELEMETRY",
        "name": "Missing telemetry",
        "description": (
            "A sensor that has previously reported has no new reading beyond the "
            "configured freshness threshold. Repeated identical outages are "
            "deduplicated until recovery. Demo threshold."
        ),
        "rule_type": "missing_telemetry",
        "metric": "freshness",
        "operator": "older_than_minutes",
        "threshold": 30.0,
        "secondary_threshold": None,
        "window_minutes": 30,
        "minimum_points": 1,
        "severity_weight": 0.50,
        "enabled": True,
        "version": 1,
        "configuration": {
            "cooldown_minutes": DEFAULT_COOLDOWN_MINUTES,
            "freshness_minutes": 30.0,
            "require_prior_readings": True,
            "demo_threshold": True,
        },
    },
    {
        "code": "SENSOR_QUALITY",
        "name": "Sensor quality anomaly",
        "description": (
            "Measurements are outside the sensor's configured valid ranges, "
            "frozen at the same value, or internally inconsistent. Ranges come "
            "from asset metadata when present. Demo thresholds."
        ),
        "rule_type": "absolute_threshold",
        "metric": "quality",
        "operator": "any",
        "threshold": 1.0,
        "secondary_threshold": None,
        "window_minutes": 30,
        "minimum_points": 4,
        "severity_weight": 0.45,
        "enabled": True,
        "version": 1,
        "configuration": {
            "cooldown_minutes": DEFAULT_COOLDOWN_MINUTES,
            "frozen_minutes": 15.0,
            "frozen_minimum_points": 5,
            "use_sensor_valid_ranges": True,
            "inconsistent_pressure_flow_ratio_max": 50.0,
            "fallback_ranges": {
                "pressure_kpa": {"min": 50.0, "max": 1600.0},
                "flow_lps": {"min": 0.0, "max": 120.0},
                "temperature_c": {"min": -10.0, "max": 70.0},
            },
            "demo_threshold": True,
        },
    },
]
