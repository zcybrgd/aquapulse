"""Central telemetry freshness, limits and unit metadata.

Freshness is measured against wall-clock UTC at query time.
Simulated historical seed ends at the frozen demo clock (2026-09-01 07:45 UTC),
so freshness depends on whether the development simulator has produced newer rows.
"""

from datetime import timedelta
from typing import Literal

FreshnessState = Literal["fresh", "stale", "offline"]

FRESH_AFTER = timedelta(minutes=15)
STALE_AFTER = timedelta(hours=2)

MAX_QUERY_RANGE = timedelta(days=7)
MAX_RAW_POINTS = 2_000
DEFAULT_LIMIT = 500
DEFAULT_RANGE = "24h"
CHUNK_INTERVAL = "1 day"

RANGE_DELTAS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}

INTERVAL_BUCKETS = {
    "raw": None,
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
}

METRIC_COLUMNS = {
    "pressure": "pressure_kpa",
    "flow": "flow_lps",
    "temperature": "temperature_c",
    "signal": "signal_strength_dbm",
    "packet_loss": "packet_loss_pct",
    "battery": "battery_pct",
}

METRIC_UNITS = {
    "pressure": {"unit": "kPa", "display_unit": "bar", "scale": 0.01},
    "flow": {"unit": "L/s", "display_unit": "m³/h", "scale": 3.6},
    "temperature": {"unit": "°C", "display_unit": "°C", "scale": 1.0},
    "signal": {"unit": "dBm", "display_unit": "dBm", "scale": 1.0},
    "packet_loss": {"unit": "%", "display_unit": "%", "scale": 1.0},
    "battery": {"unit": "%", "display_unit": "%", "scale": 1.0},
}

DATA_MODE = "simulated"

KPA_TO_BAR = 0.01
LPS_TO_M3H = 3.6

# Documented TimescaleDB policies for this step. Compression is not enabled
# automatically. Retention/deletion jobs are not activated.
INTENDED_COMPRESSION_AFTER = "7 days"
INTENDED_RAW_RETENTION = "90 days"
INTENDED_AGGREGATE_RETENTION = "longer than raw (not activated)"

SENSOR_SEED_INTERVAL = timedelta(minutes=5)
# Last 24 hours keep the original 5-minute pattern. Older days use the same
# deterministic generator so 7d/30d analytics stay reproducible.
SENSOR_SEED_HORIZON = timedelta(days=30)
SENSOR_OFFLINE_END_OFFSET = timedelta(hours=6)
