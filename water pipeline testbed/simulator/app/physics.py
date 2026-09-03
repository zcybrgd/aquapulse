"""
Pipeline physics engine.

Each sensor cluster corresponds to one pipeline segment node (pump + pipe run
+ valve + a pressure/flow/temperature sensor triplet, per the AIA's Reading
schema). State evolves once per tick:

  1. Baseline drift: small mean-reverting random walk around the segment's
     steady-state pressure/flow (so "normal" telemetry isn't perfectly flat).
  2. Environmental temperature: derived from the global environment setting
     plus per-cluster jitter.
  3. Active fault effects: applied on top of the baseline (see faults.py).
  4. Sensor-mode overrides (freeze/flatline/drift) applied last, since they
     represent what the *sensor reports*, which can diverge from the true
     physical state once communication or hardware has failed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from faults import ActiveFault, TEMP_PRESETS
from topology import SEGMENTS, get_segment


@dataclass
class ClusterState:
    sensor_cluster_id: str
    true_pressure_psi: float
    true_flow_lps: float
    reported_pressure_psi: float
    reported_flow_lps: float
    ambient_temp_c: float
    frozen_reading: tuple | None = None  # (pressure, flow) snapshot for "freeze" sensor mode
    drift_offset_pressure: float = 0.0
    drift_offset_flow: float = 0.0


class SimulationState:
    """Global mutable simulation state, shared across the FastAPI app."""

    def __init__(self, tick_seconds: float = 2.0):
        self.tick_seconds = tick_seconds
        self.running = False
        self.tick_count = 0
        self.environment_temp_c = TEMP_PRESETS["normal"]
        self.rng = random.Random(1234)

        self.clusters: dict[str, ClusterState] = {}
        for seg in SEGMENTS:
            self.clusters[seg["sensor_cluster_id"]] = ClusterState(
                sensor_cluster_id=seg["sensor_cluster_id"],
                true_pressure_psi=seg["baseline_pressure_psi"],
                true_flow_lps=seg["baseline_flow_lps"],
                reported_pressure_psi=seg["baseline_pressure_psi"],
                reported_flow_lps=seg["baseline_flow_lps"],
                ambient_temp_c=self.environment_temp_c,
            )

        # rolling telemetry windows: cluster_id -> list[dict] (max 10)
        self.windows: dict[str, list[dict]] = {cid: [] for cid in self.clusters}

        # active faults: cluster_id -> ActiveFault (one active fault per cluster for simplicity;
        # a cluster's fault must be cleared before a new one is injected)
        self.active_faults: dict[str, ActiveFault] = {}

        # Clusters where the simulated Nokia NaC CAMARA platform itself is
        # "down" (network_status calls return 5xx). This is orthogonal to
        # `active_faults` -- it exists specifically to exercise the AIA's
        # api_unavailable / insufficient_data path, as distinct from a
        # simulated UNREACHABLE/HIGH-congestion *reading* from a healthy
        # platform (see faults.py's "network_loss" / "thermal_cell_degradation").
        self.api_outage_clusters: set[str] = set()

        # event log of injections/clears, newest first
        self.fault_event_log: list[dict] = []

    def set_environment_temp(self, preset_or_value) -> float:
        if isinstance(preset_or_value, str):
            if preset_or_value not in TEMP_PRESETS:
                raise ValueError(f"Unknown temperature preset '{preset_or_value}'. Known: {list(TEMP_PRESETS)}")
            self.environment_temp_c = TEMP_PRESETS[preset_or_value]
        else:
            self.environment_temp_c = float(preset_or_value)
        return self.environment_temp_c

    def inject_fault(self, fault: ActiveFault) -> None:
        self.active_faults[fault.cluster_id] = fault
        self.fault_event_log.insert(0, {
            "action": "inject",
            "cluster_id": fault.cluster_id,
            "fault_type": fault.fault_type,
            "magnitude": fault.magnitude,
            "description": fault.effect.description,
            "tick": self.tick_count,
        })

    def clear_fault(self, cluster_id: str) -> bool:
        fault = self.active_faults.pop(cluster_id, None)
        cluster = self.clusters.get(cluster_id)
        if cluster is not None:
            cluster.frozen_reading = None
            cluster.drift_offset_pressure = 0.0
            cluster.drift_offset_flow = 0.0
        if fault is not None:
            self.fault_event_log.insert(0, {
                "action": "clear",
                "cluster_id": cluster_id,
                "fault_type": fault.fault_type,
                "magnitude": fault.magnitude,
                "tick": self.tick_count,
            })
            return True
        return False

    def clear_all_faults(self) -> None:
        for cid in list(self.active_faults.keys()):
            self.clear_fault(cid)

    def set_api_outage(self, cluster_id: str, outage: bool) -> None:
        if outage:
            self.api_outage_clusters.add(cluster_id)
        else:
            self.api_outage_clusters.discard(cluster_id)
        self.fault_event_log.insert(0, {
            "action": "api_outage_on" if outage else "api_outage_off",
            "cluster_id": cluster_id,
            "fault_type": "nokia_nac_platform_outage",
            "magnitude": "n/a",
            "tick": self.tick_count,
        })

    def reset(self) -> None:
        self.clear_all_faults()
        self.api_outage_clusters.clear()
        self.tick_count = 0
        self.environment_temp_c = TEMP_PRESETS["normal"]
        self.fault_event_log.clear()
        for seg in SEGMENTS:
            cid = seg["sensor_cluster_id"]
            self.clusters[cid] = ClusterState(
                sensor_cluster_id=cid,
                true_pressure_psi=seg["baseline_pressure_psi"],
                true_flow_lps=seg["baseline_flow_lps"],
                reported_pressure_psi=seg["baseline_pressure_psi"],
                reported_flow_lps=seg["baseline_flow_lps"],
                ambient_temp_c=self.environment_temp_c,
            )
            self.windows[cid] = []


def _mean_revert(value: float, baseline: float, strength: float, noise: float, rng: random.Random) -> float:
    reversion = (baseline - value) * strength
    jitter = rng.gauss(0, noise)
    return value + reversion + jitter


def tick(state: SimulationState) -> None:
    """Advance the simulation by one tick, mutating `state` in place."""
    state.tick_count += 1

    for cid, cluster in state.clusters.items():
        seg = get_segment(cid)
        baseline_p = seg["baseline_pressure_psi"]
        baseline_q = seg["baseline_flow_lps"]

        # 1. Baseline mean-reverting drift (normal operational noise).
        # Reversion strength is tuned so the steady-state std of pure noise
        # (noise_std / sqrt(2*strength - strength^2)) stays comfortably below
        # the seeded Z-score baseline std in agent_factory.py, even over long
        # continuous runs -- otherwise a weakly-reverting random walk can
        # eventually wander far enough to trip a false Z-score positive on
        # perfectly healthy telemetry.
        cluster.true_pressure_psi = _mean_revert(cluster.true_pressure_psi, baseline_p, 0.15, 0.12, state.rng)
        cluster.true_flow_lps = _mean_revert(cluster.true_flow_lps, baseline_q, 0.18, 0.22, state.rng)

        # 2. Ambient temperature: global environment + small per-cluster jitter
        cluster.ambient_temp_c = state.environment_temp_c + state.rng.gauss(0, 0.3)

        # 3. Active fault effects on the TRUE physical state
        fault = state.active_faults.get(cid)
        if fault is not None:
            fault.ticks_elapsed += 1
            ramp = fault.current_ramp_factor()
            eff = fault.effect

            if eff.pressure_rate_pct_per_tick:
                cluster.true_pressure_psi += baseline_p * (eff.pressure_rate_pct_per_tick / 100.0) * ramp
            if eff.flow_rate_pct_per_tick:
                cluster.true_flow_lps += baseline_q * (eff.flow_rate_pct_per_tick / 100.0) * ramp

            if eff.pressure_target_pct is not None:
                target = baseline_p * (eff.pressure_target_pct / 100.0)
                cluster.true_pressure_psi += (target - cluster.true_pressure_psi) * min(1.0, 0.3 * ramp + 0.05)
            if eff.flow_target_pct is not None:
                target = baseline_q * (eff.flow_target_pct / 100.0)
                cluster.true_flow_lps += (target - cluster.true_flow_lps) * min(1.0, 0.3 * ramp + 0.05)

            cluster.true_pressure_psi = max(0.0, cluster.true_pressure_psi)
            cluster.true_flow_lps = max(0.0, cluster.true_flow_lps)

        # 4. Reported values start from the true physical state...
        cluster.reported_pressure_psi = cluster.true_pressure_psi
        cluster.reported_flow_lps = cluster.true_flow_lps

        # ...then sensor-mode overrides distort what's actually reported.
        if fault is not None and fault.effect.sensor_mode:
            mode = fault.effect.sensor_mode
            if mode == "flatline":
                cluster.reported_pressure_psi = 0.0
                cluster.reported_flow_lps = 0.0
            elif mode == "freeze":
                if cluster.frozen_reading is None:
                    cluster.frozen_reading = (cluster.true_pressure_psi, cluster.true_flow_lps)
                cluster.reported_pressure_psi, cluster.reported_flow_lps = cluster.frozen_reading
            elif mode == "drift":
                cluster.drift_offset_pressure += baseline_p * (fault.effect.drift_pct_per_tick / 100.0)
                cluster.drift_offset_flow += baseline_q * (fault.effect.drift_pct_per_tick / 100.0) * 0.3
                cluster.reported_pressure_psi = cluster.true_pressure_psi - cluster.drift_offset_pressure
                cluster.reported_flow_lps = cluster.true_flow_lps + cluster.drift_offset_flow

        # 5. Push into the rolling telemetry window (max 10 readings, per Section 3 of the AIA spec)
        window = state.windows[cid]
        window.append({
            "pressure_psi": round(cluster.reported_pressure_psi, 2),
            "flow_rate_lps": round(cluster.reported_flow_lps, 2),
            "ambient_temp_c": round(cluster.ambient_temp_c, 2),
        })
        if len(window) > 10:
            window.pop(0)
