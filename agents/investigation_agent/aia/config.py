from __future__ import annotations

# ---------------------------------------------------------------------------
# Stage 1: Anomaly Detection
# ---------------------------------------------------------------------------

Z_SCORE_THRESHOLD = 3.0

# Rolling window (minutes) used for the deterministic rate-of-change check.
ROLLING_WINDOW_MINUTES = 5

# Sharp-deviation deterministic floors (Section 1 / 5.A.1)
INSTANT_PRESSURE_DROP_PCT_FLOOR = 15.0   # >= this % drop within the rolling window -> suspicious
INSTANT_FLOW_SURGE_PCT_FLOOR = 20.0      # >= this % surge within the rolling window -> suspicious


ISO_FOREST_MIN_BOOTSTRAP_SAMPLES = 50   # minimum samples before the ML layer is trusted
ML_TEMP_ADAPTATION_THRESHOLD_C = 50.0
ML_TEMP_ADAPTATION_TAU_SHIFT = 0.05      # widen the ML decision boundary by this much

# ---------------------------------------------------------------------------
# Stage 2: Anomaly Investigation (CAMARA disambiguation)
# ---------------------------------------------------------------------------

CONGESTION_HIGH = "HIGH"
CONGESTION_MEDIUM = "MEDIUM"
CONGESTION_LOW = "LOW"
CONGESTION_UNAVAILABLE = "UNAVAILABLE"

REACHABLE = "REACHABLE"
UNREACHABLE = "UNREACHABLE"

# Ambient temperature threshold used to diagnose thermal cell degradation
# vs. a genuine instrument fault (Section 5.B.2).
THERMAL_DEGRADATION_TEMP_C = 50.0

# insufficient_data retry / escalation schedule (Section 5.B.4)
MAX_INSUFFICIENT_DATA_RETRIES = 3  # 3rd consecutive cycle -> escalate to human operator

# Flapping-reachability escalation (Section 9, Scenario E): batches 1 & 2
# are re-queued, batch 3 triggers immediate escalation. Reuses the same
# counter/threshold as insufficient_data.
MAX_FLAPPING_RETRIES = 3

# Fallback severity tier applied when api_unavailable=True (Section 9, Scenario D)
API_UNAVAILABLE_FALLBACK_TIER = 2

# ---------------------------------------------------------------------------
# Stage 3: Deterministic Risk Assessment & Severity Tiering
# ---------------------------------------------------------------------------
# Default risk thresholds (global). Zone-specific profiles override these
# values when a segment's zone_id is found in ZONE_PROFILES below.
DEFAULT_TIER1_DELTA_P_PCT_MAX = 15.0
DEFAULT_TIER2_DELTA_P_PCT_MIN = 15.0
DEFAULT_TIER2_DELTA_P_PCT_MAX = 35.0
DEFAULT_TIER3_DELTA_P_PCT_MIN = 35.0
DEFAULT_TIER3_PRESSURE_SLOPE_MAX = -1.5  # psi/min; slope must be MORE negative than this
                                          # Calibrated for regression-based slope (Section 5.C.2).

# Backward-compatible aliases for code that uses the old names directly.
TIER1_DELTA_P_PCT_MAX = DEFAULT_TIER1_DELTA_P_PCT_MAX
TIER2_DELTA_P_PCT_MIN = DEFAULT_TIER2_DELTA_P_PCT_MIN
TIER2_DELTA_P_PCT_MAX = DEFAULT_TIER2_DELTA_P_PCT_MAX
TIER3_DELTA_P_PCT_MIN = DEFAULT_TIER3_DELTA_P_PCT_MIN
TIER3_PRESSURE_SLOPE_MAX = DEFAULT_TIER3_PRESSURE_SLOPE_MAX

TIER3_CRITICALITY_REQUIRED = 3
TIER2_CRITICALITY_TRIGGER = 2
TIER1_CRITICALITY_MAX = 1

# Emergency override: an extreme pressure drop unconditionally triggers Tier 3
# regardless of criticality, preventing a topology-cache miss or unconfigured
# segment from silently downgrading a catastrophic rupture.
TIER3_EMERGENCY_DELTA_P_PCT_MIN = 60.0

# ---------------------------------------------------------------------------
# Zone-specific threshold profiles (Section 5.C.3 extension)
# ---------------------------------------------------------------------------
# Each zone can override the default tier thresholds. This allows operators
# to tune sensitivity per geographic area (e.g. newer infrastructure in
# NEOM-North vs older pipes in NEOM-South). Segments without a zone_id or
# with an unrecognized zone fall back to the DEFAULT_* constants above.
ZONE_PROFILES: dict[str, dict[str, float]] = {
    "neom-north": {
        "tier1_delta_p_pct_max": 15.0,
        "tier2_delta_p_pct_min": 15.0,
        "tier2_delta_p_pct_max": 35.0,
        "tier3_delta_p_pct_min": 35.0,
        "tier3_pressure_slope_max": -1.5,
    },
    "neom-south": {
        "tier1_delta_p_pct_max": 12.0,
        "tier2_delta_p_pct_min": 12.0,
        "tier2_delta_p_pct_max": 30.0,
        "tier3_delta_p_pct_min": 30.0,
        "tier3_pressure_slope_max": -1.2,  # older pipes, more sensitive
    },
}


def get_zone_thresholds(zone_id: str | None) -> dict[str, float]:
    """Return the threshold profile for a given zone, falling back to defaults."""
    if zone_id and zone_id in ZONE_PROFILES:
        return ZONE_PROFILES[zone_id]
    return {
        "tier1_delta_p_pct_max": DEFAULT_TIER1_DELTA_P_PCT_MAX,
        "tier2_delta_p_pct_min": DEFAULT_TIER2_DELTA_P_PCT_MIN,
        "tier2_delta_p_pct_max": DEFAULT_TIER2_DELTA_P_PCT_MAX,
        "tier3_delta_p_pct_min": DEFAULT_TIER3_DELTA_P_PCT_MIN,
        "tier3_pressure_slope_max": DEFAULT_TIER3_PRESSURE_SLOPE_MAX,
    }


# Confidence score weights (Section 5.D). Must sum to 1.0.
CONFIDENCE_WEIGHT_TELEMETRY = 0.40
CONFIDENCE_WEIGHT_CAMARA = 0.40
CONFIDENCE_WEIGHT_TREND = 0.20
EXPECTED_TELEMETRY_WINDOW_LEN = 10  # "complete" window size for C_telemetry = 1.0

# ---------------------------------------------------------------------------
# Stage 4: AI Narration (Mistral API)
# ---------------------------------------------------------------------------
# Using the official Mistral API. Any model available on the Mistral Platform
# (e.g. open-mistral-7b, mistral-small-latest) can be used here.
LLM_MODEL = "mistral-small-latest"
LLM_BASE_URL = "https://api.mistral.ai/v1/chat/completions"
LLM_MAX_TOKENS = 400

# Prompt-injection guardrail (Section 6): only alnum + hyphen accepted for any
# field-sourced identifier that flows into the LLM prompt template.
IDENTIFIER_SANITIZATION_REGEX = r"^[a-zA-Z0-9\-]{1,64}$"

# ---------------------------------------------------------------------------
# Performance targets (Section 1 / 9) -- exposed for monitoring/tests.
# ---------------------------------------------------------------------------
AIA_PROCESSING_LATENCY_BUDGET_SECONDS = 5.0
END_TO_END_LATENCY_BUDGET_SECONDS = 30.0
TARGET_FALSE_POSITIVE_RATE = 0.02