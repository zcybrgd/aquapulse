"""Analytics windows, buckets and comparison rules.

Windows are anchored to the frozen demonstration clock (SEED_NOW) so seeded
results stay deterministic. Telemetry freshness for analytics also uses that
clock, not wall-clock UTC.
"""

from datetime import datetime, timedelta
from typing import Literal

from app.data.incidents import SEED_NOW
from app.services.telemetry_constants import DATA_MODE, SENSOR_SEED_INTERVAL

AnalyticsRange = Literal["24h", "7d", "30d"]
AnalyticsInterval = Literal["15m", "30m", "1h", "6h", "1d"]
TrendDirection = Literal["up", "down", "stable", "unavailable"]
MetricInterpretation = Literal["higher_is_better", "lower_is_better", "neutral"]

ANALYTICS_NOW = SEED_NOW
ANALYTICS_DATA_MODE = DATA_MODE
SAMPLE_INTERVAL = SENSOR_SEED_INTERVAL
SAMPLE_INTERVAL_SECONDS = int(SENSOR_SEED_INTERVAL.total_seconds())

RANGE_DELTAS: dict[str, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

DEFAULT_INTERVALS: dict[str, str] = {
    "24h": "30m",
    "7d": "6h",
    "30d": "1d",
}

INTERVAL_DELTAS: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "1d": timedelta(days=1),
}

ALLOWED_INTERVALS_FOR_RANGE: dict[str, frozenset[str]] = {
    "24h": frozenset({"15m", "30m", "1h"}),
    "7d": frozenset({"1h", "6h", "1d"}),
    "30d": frozenset({"6h", "1d"}),
}

STABLE_CHANGE_PCT = 1.0
INSUFFICIENT_ZONE_READINGS = 1

HEALTH_BANDS = (
    ("healthy", 80.0, None),
    ("fair", 60.0, 80.0),
    ("poor", None, 60.0),
)


def resolve_windows(range_key: str, *, now: datetime | None = None) -> tuple[datetime, datetime, datetime, datetime]:
    """Return current [start, end] and previous [prev_start, prev_end].

    The shared boundary belongs to the current window only: previous uses
    ``time >= prev_start AND time < start``.
    """
    if range_key not in RANGE_DELTAS:
        raise ValueError(range_key)
    end = now or ANALYTICS_NOW
    delta = RANGE_DELTAS[range_key]
    start = end - delta
    previous_end = start
    previous_start = previous_end - delta
    return start, end, previous_start, previous_end


def default_interval(range_key: str) -> str:
    return DEFAULT_INTERVALS[range_key]


def compare_values(
    current: float | None,
    previous: float | None,
) -> tuple[float | None, float | None, TrendDirection]:
    if current is None or previous is None:
        return None, None, "unavailable"
    change = current - previous
    if previous == 0:
        if current == 0:
            return 0.0, 0.0, "stable"
        return change, None, "up" if change > 0 else "down"
    change_pct = (change / abs(previous)) * 100.0
    if abs(change_pct) < STABLE_CHANGE_PCT:
        trend: TrendDirection = "stable"
    elif change > 0:
        trend = "up"
    else:
        trend = "down"
    return change, change_pct, trend


def aligned_bucket_start(start: datetime, interval: timedelta) -> datetime:
    seconds = int(interval.total_seconds())
    epoch = int(start.timestamp())
    aligned = epoch - (epoch % seconds)
    return datetime.fromtimestamp(aligned, tz=start.tzinfo)


def iter_buckets(start: datetime, end: datetime, interval: timedelta) -> list[datetime]:
    cursor = aligned_bucket_start(start, interval)
    buckets: list[datetime] = []
    while cursor <= end:
        if cursor >= start:
            buckets.append(cursor)
        cursor = cursor + interval
    return buckets
