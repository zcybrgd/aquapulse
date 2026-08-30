
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent

DATA_PATH: Path = _BASE_DIR / "data" / "water_leak_detection_1000_rows.csv"
MODEL_PATH: Path = _BASE_DIR / "artifacts" / "model.joblib"
SCALER_PATH: Path = _BASE_DIR / "artifacts" / "scaler.joblib"

# ---------------------------------------------------------------------------
# Train / Test Split
# ---------------------------------------------------------------------------
TEST_SIZE: float = 0.2
RANDOM_STATE: int = 42

# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------
RAW_FEATURE_COLUMNS: list[str] = [
    "Pressure (bar)",
    "Flow Rate (L/s)",
    "Temperature (°C)",
]

ENGINEERED_FEATURE_COLUMNS: list[str] = [
    "Pressure (bar)",
    "Flow Rate (L/s)",
    "Temperature (°C)",
    "pressure_flow_ratio",
    "hour_of_day",
]

TARGET_COLUMN: str = "Leak Status"

# ---------------------------------------------------------------------------
# Isolation Forest Hyperparameters
# ---------------------------------------------------------------------------
N_ESTIMATORS: int = 200
CONTAMINATION: float = 0.02   # ~1.9% leak rate in dataset
MAX_FEATURES: float = 1.0
BOOTSTRAP: bool = False

# ---------------------------------------------------------------------------
# Deterministic Thresholds (Z-Score Layer)
# ---------------------------------------------------------------------------
Z_SCORE_THRESHOLD: float = 3.0
PRESSURE_DROP_PCT: float = 15.0
FLOW_SURGE_PCT: float = 20.0

# ---------------------------------------------------------------------------
# Baseline Statistics (will be computed from training data and stored here
# at training time — these are placeholder defaults)
# ---------------------------------------------------------------------------
BASELINE_PRESSURE_MEAN: float = 3.22
BASELINE_PRESSURE_STD: float = 0.49
BASELINE_FLOW_MEAN: float = 125.0
BASELINE_FLOW_STD: float = 44.1
