"""
Result archive for aia_service, backed by TimescaleDB (a Postgres image).

Two tables:
  - `aia_results`: one row per investigated threat, used by the evaluation
    framework (`eval/run_eval.py`) to compare injected scenarios against the
    agent's actual output.
  - `aia_batches`: one row per processed batch, for basic throughput/latency
    monitoring.

Uses `aia.storage.TelemetryStore` is intentionally NOT reused here -- that
protocol is for archiving raw healthy telemetry (Stage 1's bypass path),
which in this testbed we simply drop (an `InMemoryTelemetryStore` is passed
to the agent; see `agent_factory.py`). This module instead archives the
AIA's *output* payloads, which is what the evaluation framework needs.
"""
from __future__ import annotations

import json
import logging
import time

import psycopg2
import psycopg2.extras

import config

logger = logging.getLogger("aia_service.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS aia_batches (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    batch_id TEXT NOT NULL,
    total_clusters_analyzed INT NOT NULL,
    anomalies_detected_count INT NOT NULL
);

CREATE TABLE IF NOT EXISTS aia_results (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    batch_id TEXT NOT NULL,
    anomaly_id TEXT NOT NULL,
    sensor_cluster_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    classification TEXT NOT NULL,
    severity_tier INT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    api_unavailable BOOLEAN NOT NULL,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_aia_results_cluster_ts ON aia_results (sensor_cluster_id, ts DESC);
"""


def _connect_with_retry(max_attempts: int = 20, delay_seconds: float = 2.0):
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return psycopg2.connect(config.POSTGRES_DSN)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Postgres not ready yet (attempt %d/%d): %s", attempt, max_attempts, exc)
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to Postgres after {max_attempts} attempts") from last_exc


def init_db() -> None:
    conn = _connect_with_retry()
    try:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA)
        conn.commit()
        logger.info("aia_service database schema ready")
    finally:
        conn.close()


def record_batch(batch_id: str, total_clusters_analyzed: int, anomalies_detected_count: int) -> None:
    conn = psycopg2.connect(config.POSTGRES_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO aia_batches (batch_id, total_clusters_analyzed, anomalies_detected_count) "
                "VALUES (%s, %s, %s)",
                (batch_id, total_clusters_analyzed, anomalies_detected_count),
            )
        conn.commit()
    except Exception:
        logger.exception("Failed to record batch in Postgres")
    finally:
        conn.close()


def record_results(batch_id: str, threats: list[dict]) -> None:
    if not threats:
        return
    conn = psycopg2.connect(config.POSTGRES_DSN)
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO aia_results "
                "(batch_id, anomaly_id, sensor_cluster_id, segment_id, classification, "
                " severity_tier, confidence_score, api_unavailable, payload) VALUES %s",
                [
                    (
                        batch_id,
                        t["anomaly_id"],
                        t["sensor_cluster_id"],
                        t["segment_id"],
                        t["classification"],
                        t["severity_tier"],
                        t["confidence_score"],
                        t["network_status"]["api_unavailable"],
                        json.dumps(t),
                    )
                    for t in threats
                ],
            )
        conn.commit()
    except Exception:
        logger.exception("Failed to record results in Postgres")
    finally:
        conn.close()


def latest_result_for_cluster(sensor_cluster_id: str, since_ts_iso: str | None = None) -> dict | None:
    conn = psycopg2.connect(config.POSTGRES_DSN)
    try:
        with conn.cursor() as cur:
            if since_ts_iso:
                cur.execute(
                    "SELECT payload FROM aia_results WHERE sensor_cluster_id = %s AND ts >= %s "
                    "ORDER BY ts DESC LIMIT 1",
                    (sensor_cluster_id, since_ts_iso),
                )
            else:
                cur.execute(
                    "SELECT payload FROM aia_results WHERE sensor_cluster_id = %s "
                    "ORDER BY ts DESC LIMIT 1",
                    (sensor_cluster_id,),
                )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()
