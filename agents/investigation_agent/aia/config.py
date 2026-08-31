"""
Configuration constants for the Anomaly Investigation Agent (AIA).

All safety-critical thresholds live here in one place so they can be
audited, tuned, and unit-tested without hunting through business logic.
Values are taken directly from the AIA Technical Specification v4.0.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Stage 1: Anomaly Detection
# ---------------------------------------------------------------------------

# Deterministic safety-floor Z-score threshold (Section 5.A.1).
# NOTE: per the "Safety Separation Rule", this threshold is NEVER adjusted
# for temperature. Only the ML layer's noise tolerance is temperature-adaptive.
Z_SCORE_THRESHOLD = 3.0

# Rolling window (minutes) used for the deterministic rate-of-change check.
ROLLING_WINDOW_MINUTES = 5

# Sharp-deviation deterministic floors (Section 1 / 5.A.1)
INSTANT_PRESSURE_DROP_PCT_FLOOR = 15.0   # >= this % drop within the rolling window -> suspicious
INSTANT_FLOW_SURGE_PCT_FLOOR = 20.0      # >= this % surge within the rolling window -> suspicious

# Isolation Forest bootstrap parameters (Section 5.A.2)
ISO_FOREST_CONTAMINATION = 0.05
ISO_FOREST_N_ESTIMATORS = 100
ISO_FOREST_RANDOM_STATE = 42
ISO_FOREST_MIN_BOOTSTRAP_SAMPLES = 50   # minimum samples before the ML layer is trusted

# Temperature-adaptive ML noise tolerance (Section 5.A.2).
# Above this temperature, the ML layer's anomaly score threshold tau is
# relaxed (made less sensitive to routine thermal noise) -- but ONLY the ML
# layer. The Z-score floors above are never touched.
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
# Reconciled Risk Tiering Matrix (Section 5.C.3):
#   Tier 1 (Minor):        delta_p_pct < 15%             AND criticality <= 1
#   Tier 2 (Moderate):     15% <= delta_p_pct < 35%       OR  criticality == 2
#   Tier 3 (Catastrophic): delta_p_pct >= 35%
#                          AND pressure_slope < -2.0 psi/min
#                          AND criticality == 3

TIER1_DELTA_P_PCT_MAX = 15.0
TIER2_DELTA_P_PCT_MIN = 15.0
TIER2_DELTA_P_PCT_MAX = 35.0
TIER3_DELTA_P_PCT_MIN = 35.0
TIER3_PRESSURE_SLOPE_MAX = -2.0  # psi/min; slope must be MORE negative than this
TIER3_CRITICALITY_REQUIRED = 3
TIER2_CRITICALITY_TRIGGER = 2
TIER1_CRITICALITY_MAX = 1

# Confidence score weights (Section 5.D). Must sum to 1.0.
CONFIDENCE_WEIGHT_TELEMETRY = 0.40
CONFIDENCE_WEIGHT_CAMARA = 0.40
CONFIDENCE_WEIGHT_TREND = 0.20
EXPECTED_TELEMETRY_WINDOW_LEN = 10  # "complete" window size for C_telemetry = 1.0

# ---------------------------------------------------------------------------
# Stage 4: AI Narration
# ---------------------------------------------------------------------------
ANTHROPIC_MODEL = "claude-sonnet-4-6"
NARRATION_MAX_TOKENS = 400

# Prompt-injection guardrail (Section 6): only alnum + hyphen accepted for any
# field-sourced identifier that flows into the LLM prompt template.
IDENTIFIER_SANITIZATION_REGEX = r"^[a-zA-Z0-9\-]{1,64}$"

# ---------------------------------------------------------------------------
# Performance targets (Section 1 / 9) -- exposed for monitoring/tests.
# ---------------------------------------------------------------------------
AIA_PROCESSING_LATENCY_BUDGET_SECONDS = 5.0
END_TO_END_LATENCY_BUDGET_SECONDS = 30.0
TARGET_FALSE_POSITIVE_RATE = 0.02
