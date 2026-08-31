

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config


# ---------------------------------------------------------------------------
# 1. Load CSV
# ---------------------------------------------------------------------------
def load_csv(path: Path | str | None = None) -> pd.DataFrame:

    path = Path(path) if path is not None else config.DATA_PATH

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)

    # Validate required columns exist
    required = {
        "Timestamp", "Sensor_ID",
        *config.RAW_FEATURE_COLUMNS,
        config.TARGET_COLUMN,
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse timestamps
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    return df


# ---------------------------------------------------------------------------
# 2. Clean Data
# ---------------------------------------------------------------------------
def clean_data(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    # Drop exact duplicates
    initial_len = len(df)
    df = df.drop_duplicates()
    dropped = initial_len - len(df)
    if dropped > 0:
        print(f"  [clean] Dropped {dropped} duplicate rows.")

    # Drop nulls in critical columns
    critical_cols = [*config.RAW_FEATURE_COLUMNS, config.TARGET_COLUMN]
    null_count = df[critical_cols].isnull().sum().sum()
    if null_count > 0:
        df = df.dropna(subset=critical_cols)
        print(f"  [clean] Dropped {null_count} rows with null values.")

    # Validate physical ranges
    df = df[df["Pressure (bar)"] > 0]
    df = df[df["Flow Rate (L/s)"] >= 0]

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 3. Feature Engineering
# ---------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    # Pressure-to-flow ratio (high ratio + low flow → possible blockage)
    # Guard against division by zero
    df["pressure_flow_ratio"] = df["Pressure (bar)"] / df["Flow Rate (L/s)"].replace(
        0, np.nan
    )
    df["pressure_flow_ratio"] = df["pressure_flow_ratio"].fillna(0.0)

    # Hour of day (captures diurnal usage patterns)
    df["hour_of_day"] = df["Timestamp"].dt.hour

    return df


# ---------------------------------------------------------------------------
# 4. Feature Matrix Extraction
# ---------------------------------------------------------------------------
def get_feature_matrix(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    target_column: str | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract feature matrix X and target vector y as numpy arrays.

    """
    feature_columns = feature_columns or config.ENGINEERED_FEATURE_COLUMNS
    target_column = target_column or config.TARGET_COLUMN

    X = df[feature_columns].values.astype(np.float64)
    y = df[target_column].values.astype(np.int64)

    return X, y


# ---------------------------------------------------------------------------
# 5. Stratified Train/Test Split
# ---------------------------------------------------------------------------
def split_data(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float | None = None,
    random_state: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Stratified train/test split preserving class balance.

    """
    test_size = test_size if test_size is not None else config.TEST_SIZE
    random_state = random_state if random_state is not None else config.RANDOM_STATE

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# 6. Compute Baselines (for Z-Score thresholds)
# ---------------------------------------------------------------------------
def compute_baselines(df: pd.DataFrame) -> dict[str, Any]:
    """Compute baseline statistics from the training data for Z-score checks.

    """
    baselines = {
        "pressure_mean": float(df["Pressure (bar)"].mean()),
        "pressure_std": float(df["Pressure (bar)"].std()),
        "flow_mean": float(df["Flow Rate (L/s)"].mean()),
        "flow_std": float(df["Flow Rate (L/s)"].std()),
    }

    return baselines
