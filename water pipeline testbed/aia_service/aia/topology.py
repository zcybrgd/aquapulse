"""
Local fast-lookup pipeline topology cache (Section 3, Phase 1 of Section 9).

Per the spec, topology is loaded ONCE at system startup into a local cache
(Redis or a TimescaleDB/Postgres table) rather than being shipped with every
telemetry batch. This module provides a small abstraction:

  - `TopologyCache` is the interface the rest of the AIA depends on.
  - `InMemoryTopologyCache` is a dict-backed implementation usable in tests,
    demos, and any environment without a live Redis instance.
  - `RedisTopologyCache` is a thin wrapper around `redis-py`, used when a
    REDIS_URL is configured. It is optional -- the `redis` package is only
    imported lazily so the rest of the AIA runs without it installed.

Each segment record contains exactly the fields Stage 3 needs:
  segment_id, criticality_score (1-3), proximity_to_reservoir_m,
  population_served, associated_valve_id.
"""
from __future__ import annotations

import json
from typing import Optional, Protocol

from pydantic import BaseModel, Field


class SegmentTopology(BaseModel):
    segment_id: str
    criticality_score: int = Field(ge=1, le=3)
    proximity_to_reservoir_m: float
    population_served: int
    associated_valve_id: str


class ClusterTopologyMapping(BaseModel):
    """Maps a sensor_cluster_id to its physical pipeline segment (Section 5.C.1)."""
    sensor_cluster_id: str
    segment: SegmentTopology


class TopologyCache(Protocol):
    def get_segment_for_cluster(self, sensor_cluster_id: str) -> Optional[SegmentTopology]: ...
    def load(self, mappings: list[ClusterTopologyMapping]) -> None: ...


class InMemoryTopologyCache:
    """Dict-backed topology cache. Default choice for tests and local demos."""

    def __init__(self) -> None:
        self._store: dict[str, SegmentTopology] = {}

    def load(self, mappings: list[ClusterTopologyMapping]) -> None:
        for m in mappings:
            self._store[m.sensor_cluster_id] = m.segment

    def get_segment_for_cluster(self, sensor_cluster_id: str) -> Optional[SegmentTopology]:
        return self._store.get(sensor_cluster_id)

    def __len__(self) -> int:
        return len(self._store)


class RedisTopologyCache:
    """
    Redis-backed topology cache for production deployment.
    Keys are namespaced `aia:topo:{sensor_cluster_id}` and store JSON-encoded
    SegmentTopology objects, matching the "local fast-lookup store" language
    in Section 3 of the spec.
    """

    def __init__(self, redis_url: str, namespace: str = "aia:topo"):
        try:
            import redis  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only without redis installed
            raise ImportError(
                "The 'redis' package is required for RedisTopologyCache. "
                "Install it with `pip install redis`, or use InMemoryTopologyCache instead."
            ) from exc
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._namespace = namespace

    def _key(self, sensor_cluster_id: str) -> str:
        return f"{self._namespace}:{sensor_cluster_id}"

    def load(self, mappings: list[ClusterTopologyMapping]) -> None:
        pipe = self._redis.pipeline()
        for m in mappings:
            pipe.set(self._key(m.sensor_cluster_id), m.segment.model_dump_json())
        pipe.execute()

    def get_segment_for_cluster(self, sensor_cluster_id: str) -> Optional[SegmentTopology]:
        raw = self._redis.get(self._key(sensor_cluster_id))
        if raw is None:
            return None
        return SegmentTopology(**json.loads(raw))


def build_default_demo_topology() -> InMemoryTopologyCache:
    """Small seed topology used by the example run / scenario tests."""
    cache = InMemoryTopologyCache()
    cache.load([
        ClusterTopologyMapping(
            sensor_cluster_id="cluster-desert-042",
            segment=SegmentTopology(
                segment_id="seg-neom-north-01",
                criticality_score=3,
                proximity_to_reservoir_m=120.0,
                population_served=45000,
                associated_valve_id="valve-neom-north-01",
            ),
        ),
        ClusterTopologyMapping(
            sensor_cluster_id="cluster-desert-043",
            segment=SegmentTopology(
                segment_id="seg-neom-north-02",
                criticality_score=2,
                proximity_to_reservoir_m=2400.0,
                population_served=8000,
                associated_valve_id="valve-neom-north-02",
            ),
        ),
        ClusterTopologyMapping(
            sensor_cluster_id="cluster-desert-044",
            segment=SegmentTopology(
                segment_id="seg-neom-north-03",
                criticality_score=1,
                proximity_to_reservoir_m=8500.0,
                population_served=12,
                associated_valve_id="valve-neom-north-03",
            ),
        ),
    ])
    return cache
