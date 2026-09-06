from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# ===========================================================================
# Application Environment / External Services
# ===========================================================================

# Project root:
#
#   investigation_agent/
#   ├── .env
#   └── aia/
#       └── config.py
#
# From aia/config.py:
#   parents[0] -> aia/
#   parents[1] -> investigation_agent/
#
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load the project's .env file explicitly.
#
# This avoids depending on the directory from which the application
# happens to be started.
load_dotenv(PROJECT_ROOT / ".env")


# ===========================================================================
# Nokia Network-as-Code / CAMARA
# ===========================================================================

# Nokia Network-as-Code RapidAPI host.
#
# This is the host used by the official Nokia Network-as-Code Python SDK.
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST")


# API key used to authenticate with Nokia Network-as-Code.
#
# The actual secret must remain in .env:
#
#   RAPIDAPI_KEY=your-key-here
#
# We intentionally use os.environ.get() here rather than os.environ[]
# so configuration loading itself does not immediately crash the
# application. The key is validated when the Nokia client is built.
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")


def get_rapidapi_key() -> str:
    """
    Return the configured Nokia Network-as-Code API key.

    Raises:
        RuntimeError:
            If RAPIDAPI_KEY is not configured.

    Returns:
        The Nokia Network-as-Code API key.
    """
    if not RAPIDAPI_KEY:
        raise RuntimeError(
            "RAPIDAPI_KEY is not configured. "
            f"Add RAPIDAPI_KEY to {PROJECT_ROOT / '.env'}."
        )

    return RAPIDAPI_KEY


# ===========================================================================
# Stage 1: Anomaly Detection
# ===========================================================================

Z_SCORE_THRESHOLD = 3.0

# Rolling window (minutes) used for the deterministic rate-of-change check.
ROLLING_WINDOW_MINUTES = 5

# Sharp-deviation deterministic floors (Section 1 / 5.A.1)
INSTANT_PRESSURE_DROP_PCT_FLOOR = 15.0
# >= this % drop within the rolling window -> suspicious

INSTANT_FLOW_SURGE_PCT_FLOOR = 20.0
# >= this % surge within the rolling window -> suspicious


ISO_FOREST_MIN_BOOTSTRAP_SAMPLES = 50
# Minimum samples before the ML layer is trusted.

ML_TEMP_ADAPTATION_THRESHOLD_C = 50.0

ML_TEMP_ADAPTATION_TAU_SHIFT = 0.05
# Widen the ML decision boundary by this much.


# ===========================================================================
# Stage 2: Anomaly Investigation (CAMARA disambiguation)
# ===========================================================================

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
MAX_INSUFFICIENT_DATA_RETRIES = 3
# 3rd consecutive cycle -> escalate to human operator.

# Flapping-reachability escalation (Section 9, Scenario E):
# batches 1 & 2 are re-queued, batch 3 triggers immediate escalation.
# Reuses the same counter/threshold as insufficient_data.
MAX_FLAPPING_RETRIES = 3

# Fallback severity tier applied when api_unavailable=True
# (Section 9, Scenario D).
API_UNAVAILABLE_FALLBACK_TIER = 2


# ===========================================================================
# Stage 3: Deterministic Risk Assessment & Severity Tiering
# ===========================================================================

# Default risk thresholds (global).
#
# Zone-specific profiles override these values when a segment's zone_id
# is found in ZONE_PROFILES below.

DEFAULT_TIER1_DELTA_P_PCT_MAX = 15.0

DEFAULT_TIER2_DELTA_P_PCT_MIN = 15.0
DEFAULT_TIER2_DELTA_P_PCT_MAX = 35.0

DEFAULT_TIER3_DELTA_P_PCT_MIN = 35.0

DEFAULT_TIER3_PRESSURE_SLOPE_MAX = -1.5
# psi/min; slope must be MORE negative than this.
# Calibrated for regression-based slope (Section 5.C.2).


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------
#
# Keep these aliases for code that still imports the old names directly.

TIER1_DELTA_P_PCT_MAX = DEFAULT_TIER1_DELTA_P_PCT_MAX

TIER2_DELTA_P_PCT_MIN = DEFAULT_TIER2_DELTA_P_PCT_MIN
TIER2_DELTA_P_PCT_MAX = DEFAULT_TIER2_DELTA_P_PCT_MAX

TIER3_DELTA_P_PCT_MIN = DEFAULT_TIER3_DELTA_P_PCT_MIN
TIER3_PRESSURE_SLOPE_MAX = DEFAULT_TIER3_PRESSURE_SLOPE_MAX


# ---------------------------------------------------------------------------
# Criticality thresholds
# ---------------------------------------------------------------------------

TIER3_CRITICALITY_REQUIRED = 3

TIER2_CRITICALITY_TRIGGER = 2

TIER1_CRITICALITY_MAX = 1


# ---------------------------------------------------------------------------
# Emergency override
# ---------------------------------------------------------------------------
#
# An extreme pressure drop unconditionally triggers Tier 3 regardless
# of criticality.
#
# This prevents a topology-cache miss or unconfigured segment from
# silently downgrading a catastrophic rupture.

TIER3_EMERGENCY_DELTA_P_PCT_MIN = 60.0


# ===========================================================================
# Zone-specific threshold profiles
# ===========================================================================
#
# Each zone can override the default tier thresholds.
#
# This allows operators to tune sensitivity per geographic area
# (e.g. newer infrastructure in NEOM-North vs. older pipes in NEOM-South).
#
# Segments without a zone_id or with an unrecognized zone fall back
# to the DEFAULT_* constants above.

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
        "tier3_pressure_slope_max": -1.2,
        # Older pipes, more sensitive.
    },
}


def get_zone_thresholds(zone_id: str | None) -> dict[str, float]:
    """
    Return the threshold profile for a given zone.

    If the zone is configured in ZONE_PROFILES, its custom thresholds
    are returned. Otherwise, the global default thresholds are returned.
    """
    if zone_id and zone_id in ZONE_PROFILES:
        return ZONE_PROFILES[zone_id]

    return {
        "tier1_delta_p_pct_max": DEFAULT_TIER1_DELTA_P_PCT_MAX,
        "tier2_delta_p_pct_min": DEFAULT_TIER2_DELTA_P_PCT_MIN,
        "tier2_delta_p_pct_max": DEFAULT_TIER2_DELTA_P_PCT_MAX,
        "tier3_delta_p_pct_min": DEFAULT_TIER3_DELTA_P_PCT_MIN,
        "tier3_pressure_slope_max": DEFAULT_TIER3_PRESSURE_SLOPE_MAX,
    }


# ---------------------------------------------------------------------------
# Confidence score weights (Section 5.D)
# ---------------------------------------------------------------------------
#
# These weights must sum to 1.0.

CONFIDENCE_WEIGHT_TELEMETRY = 0.40

CONFIDENCE_WEIGHT_CAMARA = 0.40

CONFIDENCE_WEIGHT_TREND = 0.20

EXPECTED_TELEMETRY_WINDOW_LEN = 10
# "Complete" window size for C_telemetry = 1.0.


# ===========================================================================
# Stage 4: AI Narration (Groq API -- OpenAI-compatible)
# ===========================================================================

# Groq's OpenAI-compatible endpoint.
LLM_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model used for AI narration. Groq free tier: ~30 req/min, 1000 req/day
# for chat models (verify current limits on console.groq.com/docs/rate-limits).
LLM_MODEL = "openai/gpt-oss-20b"


# ---------------------------------------------------------------------------
# Prompt-injection guardrail (Section 6)
# ---------------------------------------------------------------------------
#
# Only alphanumeric characters and hyphens are accepted for any
# field-sourced identifier that flows into the LLM prompt template.

IDENTIFIER_SANITIZATION_REGEX = r"^[a-zA-Z0-9\-]{1,64}$"


# ===========================================================================
# Performance Targets
# ===========================================================================
#
# Section 1 / 9 -- exposed for monitoring and tests.

AIA_PROCESSING_LATENCY_BUDGET_SECONDS = 5.0

END_TO_END_LATENCY_BUDGET_SECONDS = 30.0

TARGET_FALSE_POSITIVE_RATE = 0.02