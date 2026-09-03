"""
Builds a StreamingBatch-shaped JSON payload (matching the AIA's
`StreamingBatch` / `TelemetryWindow` / `Reading` Pydantic schema exactly) from
the current simulation state, ready to POST to `aia_service`.

Only clusters with a full-ish window (>= 2 readings) are included, so the
very first tick after startup/reset doesn't emit a degenerate single-point
window.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from network_sim import derive_network_state
from physics import SimulationState


def build_batch(state: SimulationState) -> dict:
    now = datetime.now(timezone.utc)
    windows = []

    for cid, readings in state.windows.items():
        if len(readings) < 2:
            continue
        fault = state.active_faults.get(cid)
        cluster_state = state.clusters[cid]
        net = derive_network_state(cluster_state.ambient_temp_c, fault, state.rng)

        # Reconstruct timestamps spaced one simulated "minute" apart, ending now,
        # matching the AIA spec's 1-minute-interval rolling window convention.
        n = len(readings)
        timestamped_readings = [
            {
                "timestamp": (now - timedelta(minutes=(n - 1 - i))).isoformat(),
                "pressure_psi": r["pressure_psi"],
                "flow_rate_lps": r["flow_rate_lps"],
                "ambient_temp_c": r["ambient_temp_c"],
            }
            for i, r in enumerate(readings)
        ]

        windows.append({
            "sensor_cluster_id": cid,
            "network_metadata": {
                "signal_strength_dbm": net["signal_strength_dbm"],
                "packet_loss_pct": net["packet_loss_pct"],
            },
            "readings": timestamped_readings,
        })

    return {
        "batch_id": f"sim-{uuid.uuid4().hex[:12]}",
        "timestamp": now.isoformat(),
        "telemetry_windows": windows,
    }
