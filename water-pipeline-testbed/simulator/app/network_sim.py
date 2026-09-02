"""
Simulated cellular/network layer for each sensor cluster.

This is what stands in for the real Nokia NaC CAMARA platform in the
testbed. `aia_service` queries this via HTTP (see `main.py`'s
`/network_status/{cluster_id}` endpoint) through a `SimulatedCamaraClient`
that implements the AIA's `CamaraClient` protocol.

Baseline network health is a function of ambient temperature (heat degrades
desert cell towers) plus per-cluster distance-from-reservoir jitter (a proxy
for backhaul quality). Active faults can force explicit overrides (see
`faults.FaultEffect.network_reachable/network_congestion/...`), which always
take precedence over the derived baseline -- this is what lets a scenario
say "this is a pure connectivity event" or "this is a pure hardware event"
independent of what the physical telemetry looks like.
"""
from __future__ import annotations

import random

from faults import ActiveFault

THERMAL_DEGRADATION_TEMP_C = 50.0


def derive_network_state(
    ambient_temp_c: float,
    fault: ActiveFault | None,
    rng: random.Random,
) -> dict:
    """
    Returns a dict with reachability, congestion, signal_strength_dbm,
    packet_loss_pct -- combining the temperature-driven baseline with any
    fault override.
    """
    # Baseline: heat degrades signal quality; below the thermal-degradation
    # threshold the network is healthy almost all the time.
    if ambient_temp_c >= THERMAL_DEGRADATION_TEMP_C:
        base_congestion = "HIGH" if rng.random() < 0.85 else "MEDIUM"
        base_signal = int(rng.uniform(-118, -100))
        base_packet_loss = round(rng.uniform(8.0, 25.0), 1)
        base_reachable = rng.random() > 0.15  # heat alone rarely drops reachability outright
    elif ambient_temp_c >= 45.0:
        base_congestion = "MEDIUM" if rng.random() < 0.6 else "LOW"
        base_signal = int(rng.uniform(-100, -85))
        base_packet_loss = round(rng.uniform(1.0, 8.0), 1)
        base_reachable = True
    else:
        base_congestion = "LOW"
        base_signal = int(rng.uniform(-85, -65))
        base_packet_loss = round(rng.uniform(0.0, 1.5), 1)
        base_reachable = True

    reachable = base_reachable
    congestion = base_congestion
    signal = base_signal
    packet_loss = base_packet_loss

    if fault is not None:
        eff = fault.effect
        if eff.network_reachable is not None:
            reachable = eff.network_reachable
        if eff.network_congestion is not None:
            congestion = eff.network_congestion
        if eff.packet_loss_pct_override is not None:
            packet_loss = eff.packet_loss_pct_override
        if eff.signal_dbm_override is not None:
            signal = eff.signal_dbm_override

    return {
        "reachable": reachable,
        "congestion": congestion,
        "signal_strength_dbm": signal,
        "packet_loss_pct": packet_loss,
    }
