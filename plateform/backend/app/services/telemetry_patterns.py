from __future__ import annotations

from datetime import datetime, timezone
from math import cos, sin

from app.data.incidents import SEED_NOW


def seed_source_id(external_id: str, when: datetime) -> str:
    stamp = when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"seed:{external_id}:{stamp}"


def simulator_source_id(external_id: str, when: datetime) -> str:
    stamp = when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"sim:{external_id}:{stamp}"


SCENARIOS = (
    "normal",
    "pressure_drop",
    "flow_surge",
    "combined_leak_pattern",
    "connectivity_degradation",
    "frozen_sensor",
    "missing_telemetry",
)


def scenario_reading_values(
    external_id: str,
    when: datetime,
    status: str,
    *,
    scenario: str,
    step: int,
    total_steps: int,
) -> dict[str, float | int | None] | None:
    """Deterministic scenario overlay. missing_telemetry returns None (skip write)."""
    baseline = reading_values(external_id, when, status)
    name = scenario if scenario in SCENARIOS else "normal"
    if name == "missing_telemetry":
        return None
    if name == "normal":
        return baseline
    steps = max(1, total_steps)
    progress = step / max(1, steps - 1) if steps > 1 else 1.0

    if name == "pressure_drop":
        drop = 0.18 * progress
        baseline["pressure_kpa"] = round(float(baseline["pressure_kpa"]) * (1.0 - drop), 2)
        return baseline
    if name == "flow_surge":
        surge = 0.22 * progress
        baseline["flow_lps"] = round(float(baseline["flow_lps"]) * (1.0 + surge), 3)
        return baseline
    if name == "combined_leak_pattern":
        baseline["pressure_kpa"] = round(float(baseline["pressure_kpa"]) * (1.0 - 0.18 * progress), 2)
        baseline["flow_lps"] = round(float(baseline["flow_lps"]) * (1.0 + 0.22 * progress), 3)
        return baseline
    if name == "connectivity_degradation":
        baseline["packet_loss_pct"] = round(4.0 + 14.0 * progress, 2)
        baseline["signal_strength_dbm"] = int(-82 - 24 * progress)
        return baseline
    if name == "frozen_sensor":
        frozen = reading_values(external_id, SEED_NOW.replace(minute=0, second=0, microsecond=0), status)
        return frozen
    return baseline


def _phase(external_id: str) -> float:
    return sum(ord(character) for character in external_id) % 360


def reading_values(external_id: str, when: datetime, status: str) -> dict[str, float | int | None]:
    """Deterministic simulated measurements. Identical inputs produce identical outputs."""
    minutes = int((when - SEED_NOW).total_seconds() // 60)
    phase = _phase(external_id)
    wave = sin((minutes + phase) / 37.0)
    drift = cos((minutes + phase) / 91.0)

    pressure = 412.0 + wave * 8.5 + (phase % 7) * 0.4
    flow = 54.8 + wave * 3.2 + drift * 1.1
    temperature = 24.6 + wave * 1.4
    signal = -68 + int(round(wave * 4)) - (phase % 5)
    packet_loss = max(0.15, 0.45 + abs(wave) * 0.35)
    battery = 86.0 - abs(drift) * 4.0 - (phase % 9) * 0.3

    if status == "degraded":
        signal -= 18
        packet_loss = min(12.0, 3.8 + abs(wave) * 3.2)
        battery = max(40.0, battery - 18)
        pressure += wave * 6
    elif status == "offline":
        signal = -112
        packet_loss = min(24.0, 9.0 + abs(wave) * 4.0)
        battery = max(3.0, 12.0 + wave)
        pressure = 398.0 + wave * 2

    return {
        "pressure_kpa": round(pressure, 2),
        "flow_lps": round(flow, 3),
        "temperature_c": round(temperature, 2),
        "signal_strength_dbm": int(signal),
        "packet_loss_pct": round(packet_loss, 2),
        "battery_pct": round(max(0.0, min(100.0, battery)), 1),
    }
