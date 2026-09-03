"""
Raw per-device sensor/actuator logs.

This is deliberately separate from `telemetry.py` (which builds the
AIA-facing `StreamingBatch`) and from `main.py`'s `sim:state` broadcast
(which is an aggregated snapshot for the dashboard's readout table). This
module produces what an individual field device would actually log --
one entry per sensor/actuator per tick, with no interpretation attached.

The testbed's job stops at "Simulate -> Measure -> Generate telemetry/logs
-> Send logs". These raw logs are shown in the dashboard's "Raw Sensor Logs"
panel purely as evidence of what's flowing into the Anomaly Investigation
Agent -- nothing here ever states or implies a diagnosis (no "LEAK
DETECTED", no severity, no anomaly flag). Deciding what the data means is
the Anomaly Investigation Agent's job, not the testbed's.
"""
from __future__ import annotations

from datetime import datetime, timezone

from physics import SimulationState
from topology import get_segment


def _sensor_status(cluster_id: str, state: SimulationState, sensor_kind: str) -> str:
    """
    Device-level operational status, derived only from the sensor's own
    communication/hardware state (frozen/flatlined) -- never from whether
    the underlying reading looks "abnormal". A sensor reporting a real
    physical leak is still `operational`; only a hardware/comms failure on
    that specific device changes its status.
    """
    fault = state.active_faults.get(cluster_id)
    if fault is None:
        return "operational"
    mode = fault.effect.sensor_mode
    if mode == "flatline":
        return "fault"
    if mode == "freeze":
        return "stale"
    if mode == "drift":
        return "operational"  # the device believes it's fine; that's the point
    return "operational"


def build_raw_logs(state: SimulationState) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    logs: list[dict] = []

    for cid, cluster in state.clusters.items():
        seg = get_segment(cid)
        status = _sensor_status(cid, state, "physical")
        outage = cid in state.api_outage_clusters
        net_status = "unavailable" if outage else "operational"

        logs.append({
            "timestamp": now,
            "device_id": f"{seg['segment_id']}-PRS-01".upper(),
            "device_type": "pressure_sensor",
            "sensor_cluster_id": cid,
            "measurement": "pressure",
            "value": round(cluster.reported_pressure_psi, 2),
            "unit": "psi",
            "expected_range": {
                "min": round(seg["baseline_pressure_psi"] * 0.85, 1),
                "max": round(seg["baseline_pressure_psi"] * 1.15, 1),
            },
            "status": status,
        })
        logs.append({
            "timestamp": now,
            "device_id": f"{seg['segment_id']}-FLW-01".upper(),
            "device_type": "flow_sensor",
            "sensor_cluster_id": cid,
            "measurement": "flow_rate",
            "value": round(cluster.reported_flow_lps, 2),
            "unit": "L/s",
            "expected_range": {
                "min": round(seg["baseline_flow_lps"] * 0.8, 1),
                "max": round(seg["baseline_flow_lps"] * 1.2, 1),
            },
            "status": status,
        })
        logs.append({
            "timestamp": now,
            "device_id": f"{seg['segment_id']}-TMP-01".upper(),
            "device_type": "temperature_sensor",
            "sensor_cluster_id": cid,
            "measurement": "ambient_temperature",
            "value": round(cluster.ambient_temp_c, 2),
            "unit": "C",
            "expected_range": {"min": 15.0, "max": 55.0},
            "status": "operational",
        })
        logs.append({
            "timestamp": now,
            "device_id": f"{seg['segment_id']}-NET-01".upper(),
            "device_type": "cellular_modem",
            "sensor_cluster_id": cid,
            "measurement": "connectivity",
            "value": None,
            "unit": None,
            "status": net_status,
        })

    return logs
