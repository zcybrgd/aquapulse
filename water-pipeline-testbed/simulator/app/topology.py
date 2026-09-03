"""
Shared pipeline topology for the water-pipeline testbed.

This is the single source of truth for the simulated network's physical
layout: which sensor clusters exist, which pipeline segment each belongs to,
and that segment's criticality/valve metadata. It's intentionally duplicated
(byte-for-byte) into both `simulator/app/topology.py` and
`aia_service/app/topology.py` rather than shared via a package, so each
Docker image stays independently buildable with no cross-service import
path. If you change one, change the other.
"""
from __future__ import annotations

SEGMENTS = [
    {
        "sensor_cluster_id": "cluster-desert-042",
        "segment_id": "seg-neom-north-01",
        "criticality_score": 3,
        "proximity_to_reservoir_m": 120.0,
        "population_served": 45000,
        "associated_valve_id": "valve-neom-north-01",
        "baseline_pressure_psi": 45.0,
        "baseline_flow_lps": 80.0,
    },
    {
        "sensor_cluster_id": "cluster-desert-043",
        "segment_id": "seg-neom-north-02",
        "criticality_score": 2,
        "proximity_to_reservoir_m": 2400.0,
        "population_served": 8000,
        "associated_valve_id": "valve-neom-north-02",
        "baseline_pressure_psi": 42.0,
        "baseline_flow_lps": 60.0,
    },
    {
        "sensor_cluster_id": "cluster-desert-044",
        "segment_id": "seg-neom-north-03",
        "criticality_score": 1,
        "proximity_to_reservoir_m": 8500.0,
        "population_served": 12,
        "associated_valve_id": "valve-neom-north-03",
        "baseline_pressure_psi": 38.0,
        "baseline_flow_lps": 15.0,
    },
    {
        "sensor_cluster_id": "cluster-desert-045",
        "segment_id": "seg-neom-east-01",
        "criticality_score": 2,
        "proximity_to_reservoir_m": 3000.0,
        "population_served": 6000,
        "associated_valve_id": "valve-neom-east-01",
        "baseline_pressure_psi": 40.0,
        "baseline_flow_lps": 55.0,
    },
    {
        "sensor_cluster_id": "cluster-desert-046",
        "segment_id": "seg-neom-west-01",
        "criticality_score": 1,
        "proximity_to_reservoir_m": 9000.0,
        "population_served": 500,
        "associated_valve_id": "valve-neom-west-01",
        "baseline_pressure_psi": 37.0,
        "baseline_flow_lps": 20.0,
    },
]

CLUSTER_IDS = [s["sensor_cluster_id"] for s in SEGMENTS]


def get_segment(sensor_cluster_id: str) -> dict:
    for s in SEGMENTS:
        if s["sensor_cluster_id"] == sensor_cluster_id:
            return s
    raise KeyError(sensor_cluster_id)
