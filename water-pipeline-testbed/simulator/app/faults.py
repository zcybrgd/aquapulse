"""
Fault injection engine.

Rather than hand-coding a bespoke function per named scenario (leak, rupture,
pump failure, valve stuck, sensor drift, ...), every fault type is expressed
as a small, composable `FaultEffect`: a set of per-tick deltas applied to a
cluster's physical state, plus optional "sensor mode" and "network override"
flags. Adding a new scenario later just means adding one entry to
`FAULT_LIBRARY` -- no changes to the simulation loop are required.

Effect fields:
  pressure_rate_pct_per_tick   -- % of baseline pressure removed/added per tick
  flow_rate_pct_per_tick       -- % of baseline flow removed/added per tick
  pressure_target_pct          -- if set, pressure moves toward this % of baseline
                                   instead of drifting indefinitely (used for
                                   step-like faults such as a stuck valve)
  flow_target_pct              -- same, for flow
  onset                        -- "sudden" (full effect applied immediately) or
                                   "gradual" (effect ramps in over `ramp_ticks`)
  ramp_ticks                   -- ticks to reach full magnitude, for gradual onset
  sensor_mode                  -- None | "freeze" | "flatline" | "drift"
                                   freeze: sensor keeps reporting its last
                                       pre-fault reading (stale telemetry)
                                   flatline: sensor reports 0.0 / 0.0
                                   drift: sensor reading is offset by a slowly
                                       growing bias, independent of the real
                                       physical value (miscalibration)
  network_reachable            -- force CAMARA reachability override (None = derive normally)
  network_congestion           -- force CAMARA congestion override (None = derive normally)
  packet_loss_pct_override     -- force telemetry-reported packet loss
  signal_dbm_override           -- force telemetry-reported signal strength
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FaultEffect:
    pressure_rate_pct_per_tick: float = 0.0
    flow_rate_pct_per_tick: float = 0.0
    pressure_target_pct: Optional[float] = None
    flow_target_pct: Optional[float] = None
    onset: str = "gradual"          # "sudden" | "gradual"
    ramp_ticks: int = 5
    sensor_mode: Optional[str] = None  # None | "freeze" | "flatline" | "drift"
    drift_pct_per_tick: float = 0.0
    network_reachable: Optional[bool] = None
    network_congestion: Optional[str] = None  # "LOW" | "MEDIUM" | "HIGH"
    packet_loss_pct_override: Optional[float] = None
    signal_dbm_override: Optional[int] = None
    description: str = ""


# Magnitude presets used by leak-like faults (small/medium/large).
LEAK_MAGNITUDES = {
    "small": FaultEffect(
        pressure_rate_pct_per_tick=-0.8, flow_rate_pct_per_tick=1.2,
        onset="gradual", ramp_ticks=8,
        description="Small pinhole leak: slow pressure bleed, modest flow increase.",
    ),
    "medium": FaultEffect(
        pressure_rate_pct_per_tick=-2.5, flow_rate_pct_per_tick=4.0,
        onset="gradual", ramp_ticks=5,
        description="Medium leak: progressive crack, steady pressure/flow drift.",
    ),
    "large": FaultEffect(
        pressure_rate_pct_per_tick=-6.0, flow_rate_pct_per_tick=9.0,
        onset="sudden", ramp_ticks=2,
        description="Large leak: rapid pressure collapse, sharp flow surge.",
    ),
}

TEMP_PRESETS = {
    "normal": 38.0,
    "high": 47.0,
    "extreme": 53.0,
}

FAULT_LIBRARY: dict[str, dict] = {
    "leak": {
        "small": LEAK_MAGNITUDES["small"],
        "medium": LEAK_MAGNITUDES["medium"],
        "large": LEAK_MAGNITUDES["large"],
    },
    "pipe_rupture": {
        "default": FaultEffect(
            pressure_rate_pct_per_tick=-15.0, flow_rate_pct_per_tick=20.0,
            onset="sudden", ramp_ticks=1,
            description="Catastrophic pipeline rupture: near-instant collapse.",
        ),
    },
    "pressure_spike": {
        "default": FaultEffect(
            pressure_target_pct=140.0, onset="sudden", ramp_ticks=3,
            description="Valve closure / surge event: pressure spikes well above baseline.",
        ),
    },
    "pressure_drop": {
        "default": FaultEffect(
            pressure_rate_pct_per_tick=-1.5, onset="gradual", ramp_ticks=10,
            description="Upstream blockage or supply reduction: pressure falls without a flow surge.",
        ),
    },
    "pump_failure": {
        "default": FaultEffect(
            pressure_target_pct=10.0, flow_target_pct=5.0, onset="sudden", ramp_ticks=2,
            description="Pump failure: pressure and flow collapse toward near-zero.",
        ),
    },
    "pump_degradation": {
        "default": FaultEffect(
            pressure_rate_pct_per_tick=-0.6, flow_rate_pct_per_tick=-0.6,
            onset="gradual", ramp_ticks=20,
            description="Aging/failing pump: slow decline in both pressure and flow.",
        ),
    },
    "valve_stuck_open": {
        "default": FaultEffect(
            pressure_target_pct=70.0, flow_target_pct=160.0, onset="gradual", ramp_ticks=4,
            description="Valve stuck open: uncontrolled excess flow, pressure sags.",
        ),
    },
    "valve_stuck_closed": {
        "default": FaultEffect(
            pressure_target_pct=180.0, flow_target_pct=5.0, onset="gradual", ramp_ticks=4,
            description="Valve stuck closed: flow chokes off, upstream pressure builds.",
        ),
    },
    "sensor_failure": {
        "default": FaultEffect(
            sensor_mode="flatline", onset="sudden", ramp_ticks=1,
            network_reachable=False, network_congestion="LOW",
            description="Hardware sensor failure: flatlined reading, device unreachable, network otherwise healthy.",
        ),
    },
    "sensor_drift": {
        "default": FaultEffect(
            sensor_mode="drift", drift_pct_per_tick=0.4, onset="gradual", ramp_ticks=1,
            description="Miscalibrated sensor: reported values slowly diverge from the true physical state.",
        ),
    },
    "sensor_comm_loss": {
        "default": FaultEffect(
            sensor_mode="freeze", onset="sudden", ramp_ticks=1,
            network_reachable=False,
            description="Cellular/radio dropout: sensor readings freeze at their last known value.",
        ),
    },
    "high_flow": {
        "default": FaultEffect(
            flow_rate_pct_per_tick=3.0, onset="gradual", ramp_ticks=6,
            description="Abnormal demand surge: flow climbs without a matching pressure drop.",
        ),
    },
    "low_flow": {
        "default": FaultEffect(
            flow_rate_pct_per_tick=-3.0, onset="gradual", ramp_ticks=6,
            description="Abnormally low flow: possible partial blockage or demand collapse.",
        ),
    },
    "network_loss": {
        "default": FaultEffect(
            network_reachable=False, network_congestion="LOW",
            packet_loss_pct_override=100.0, signal_dbm_override=-999,
            description="Pure connectivity loss with no physical fault: tests false-positive resistance.",
        ),
    },
    "thermal_cell_degradation": {
        "default": FaultEffect(
            sensor_mode="drift", drift_pct_per_tick=2.0,
            network_reachable=False, network_congestion="HIGH",
            packet_loss_pct_override=45.0, signal_dbm_override=-110,
            description=(
                "Extreme-heat cell tower degradation: garbled/drifting telemetry "
                "reports plus high congestion and an unreachable device -- the "
                "underlying pipe is actually healthy."
            ),
        ),
    },
}


@dataclass
class ActiveFault:
    cluster_id: str
    fault_type: str
    magnitude: str
    effect: FaultEffect
    injected_at: float = field(default_factory=time.time)
    ticks_elapsed: int = 0

    def current_ramp_factor(self) -> float:
        if self.effect.onset == "sudden":
            return 1.0
        self_ticks = max(1, self.effect.ramp_ticks)
        return min(1.0, self.ticks_elapsed / self_ticks)


def build_fault(fault_type: str, magnitude: str, cluster_id: str) -> ActiveFault:
    if fault_type not in FAULT_LIBRARY:
        raise ValueError(f"Unknown fault_type '{fault_type}'. Known: {list(FAULT_LIBRARY)}")
    variants = FAULT_LIBRARY[fault_type]
    key = magnitude if magnitude in variants else "default"
    if key not in variants:
        raise ValueError(f"Unknown magnitude '{magnitude}' for fault '{fault_type}'. Known: {list(variants)}")
    return ActiveFault(cluster_id=cluster_id, fault_type=fault_type, magnitude=magnitude, effect=variants[key])


def list_available_faults() -> dict[str, list[str]]:
    return {ft: list(variants.keys()) for ft, variants in FAULT_LIBRARY.items()}
