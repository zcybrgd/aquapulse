
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "aia", "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
DATASET_PATH = os.path.join(DATA_DIR, "leak_detection_dataset.csv")

# ---------------------------------------------------------------------------
# Data split
# ---------------------------------------------------------------------------
TEST_SIZE = 0.20
VAL_SIZE = 0.15
RANDOM_STATE = 42

# ---------------------------------------------------------------------------
# Features (v2 — calculées à partir des séries temporelles brutes)
# ---------------------------------------------------------------------------
NUMERICAL_FEATURES = [
    "p_mean",
    "p_std",
    "p_min",
    "p_max",
    "p_drop_pct",
    "p_slope",
    "p_rolling_std_5",
    "p_jitter",
    "q_mean",
    "q_std",
    "q_surge_pct",
    "q_slope",
    "pq_corr",
    "t_mean",
    "t_max",
    "zero_count",
    "pipe_diameter_mm",
    "pipe_age_years",
    "hour_of_day",
]

CATEGORICAL_FEATURES = [
    "pipe_material",
]

TARGET = "leak"

# ---------------------------------------------------------------------------
# Model hyperparameters
# ---------------------------------------------------------------------------
ISO_FOREST_PARAMS = {
    "n_estimators": 200,
    "contamination": 0.40,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}

RF_PARAMS = {
    "n_estimators": 300,
    "max_depth": 10,
    "min_samples_split": 10,
    "min_samples_leaf": 4,
    "class_weight": "balanced",
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}

GB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "random_state": RANDOM_STATE,
}

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
PRIMARY_METRIC = "recall"
CLASSIFICATION_THRESHOLD = 0.5
