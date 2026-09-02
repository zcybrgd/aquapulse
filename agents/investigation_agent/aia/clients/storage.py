"""
TimescaleDB archival for normal (non-suspicious) telemetry (Section 2, Stage 1
deliverable: "Normal logs are written directly to TimescaleDB and bypassed").

Provides a small `TelemetryStore` protocol plus an in-memory implementation
for tests/demos and a `TimescaleDBStore` for production, which uses
psycopg2/SQLAlchemy against a hypertable. The `TimescaleDBStore` is optional
at import time -- `psycopg2` is only imported when it's actually constructed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from aia.models import TelemetryWindow


class TelemetryStore(Protocol):
    def archive_normal_window(self, window: TelemetryWindow) -> None: ...


@dataclass
class InMemoryTelemetryStore:
    """Used in tests/demos; keeps archived windows in a list for inspection."""
    archived: list[TelemetryWindow] = field(default_factory=list)

    def archive_normal_window(self, window: TelemetryWindow) -> None:
        self.archived.append(window)


class TimescaleDBStore:
    """
    Production TimescaleDB sink. Expects a hypertable roughly shaped like:

        CREATE TABLE telemetry_archive (
            time            TIMESTAMPTZ NOT NULL,
            sensor_cluster_id TEXT NOT NULL,
            pressure_psi    DOUBLE PRECISION,
            flow_rate_lps   DOUBLE PRECISION,
            ambient_temp_c  DOUBLE PRECISION
        );
        SELECT create_hypertable('telemetry_archive', 'time');

    Uses a single persistent connection (lazily initialized) to avoid
    exhausting the connection pool when archiving hundreds of healthy
    windows per batch. Call `close()` at shutdown for clean teardown.
    """

    def __init__(self, dsn: str):
        import psycopg2  # imported lazily; optional dependency

        self._psycopg2 = psycopg2
        self._dsn = dsn
        self._conn = None

    def _get_connection(self):
        """Return the persistent connection, reconnecting if needed."""
        if self._conn is None or self._conn.closed:
            self._conn = self._psycopg2.connect(self._dsn)
        return self._conn

    def archive_normal_window(self, window: TelemetryWindow) -> None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO telemetry_archive
                        (time, sensor_cluster_id, pressure_psi, flow_rate_lps, ambient_temp_c)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            r.timestamp,
                            window.sensor_cluster_id,
                            r.pressure_psi,
                            r.flow_rate_lps,
                            r.ambient_temp_c,
                        )
                        for r in window.readings
                    ],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        """Release the database connection for clean shutdown."""
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
