from __future__ import annotations

import argparse
import math
import os
import random

import numpy as np
import pandas as pd


PIPE_CONFIGS = [
    {"diameter_mm": 400, "nominal_psi": 45.0, "nominal_flow": 80.0, "material": "Steel"},
    {"diameter_mm": 300, "nominal_psi": 42.0, "nominal_flow": 60.0, "material": "HDPE"},
    {"diameter_mm": 250, "nominal_psi": 40.0, "nominal_flow": 50.0, "material": "PVC"},
    {"diameter_mm": 200, "nominal_psi": 38.0, "nominal_flow": 35.0, "material": "HDPE"},
    {"diameter_mm": 150, "nominal_psi": 35.0, "nominal_flow": 25.0, "material": "PVC"},
    {"diameter_mm": 100, "nominal_psi": 30.0, "nominal_flow": 15.0, "material": "Cast Iron"},
]


PIPE_ELASTICITY = {
    "HDPE": 1.00,       # most elastic in our set -> area grows fastest with pressure
    "PVC": 0.35,        # intermediate stiffness
    "Steel": 0.05,      # rigid, close to fixed-area behaviour
    "Cast Iron": 0.03,  # most rigid -> fixed-area assumption nearly exact
}

HOURLY_DEMAND = [
    0.60, 0.55, 0.50, 0.50, 0.55, 0.65,
    0.80, 0.95, 1.10, 1.05, 0.95, 0.90,
    0.85, 0.85, 0.90, 0.95, 1.00, 1.10,
    1.15, 1.20, 1.10, 0.95, 0.80, 0.70,
]

WEEKDAY_FACTOR = [1.00, 1.00, 1.00, 1.00, 1.02, 0.90, 0.85]  # Mon..Sun
DEMAND_NOISE_STD = 0.05  # matches LeakDB's uncR=0.05 order of magnitude


def _demand_multiplier(hour: int, day_of_week: int) -> float:
    """Combined hourly x weekday x random demand multiplier.

    day_of_week: 0=Monday ... 6=Sunday.
    """
    base = HOURLY_DEMAND[hour] * WEEKDAY_FACTOR[day_of_week]
    noise = np.random.normal(0, DEMAND_NOISE_STD)
    return base * (1 + noise)


WINDOW_SIZE = 10
N_SENSORS = 20  # sensor pool size

PIPE_PARAM_UNCERTAINTY = 0.10  # +/-10%, same order of magnitude as LeakDB's qunc range


def _perturbed_pipe(pipe: dict) -> dict:

    p = dict(pipe)
    p["nominal_psi"] = pipe["nominal_psi"] * (1 + np.random.uniform(-PIPE_PARAM_UNCERTAINTY, PIPE_PARAM_UNCERTAINTY))
    p["nominal_flow"] = pipe["nominal_flow"] * (1 + np.random.uniform(-PIPE_PARAM_UNCERTAINTY, PIPE_PARAM_UNCERTAINTY))
    return p

# each sensor has a fixed bias and noise level (calibration)
def _build_sensor_pool(n: int, seed: int) -> list[dict]:
    rng = np.random.RandomState(seed + 999)
    sensors = []
    for i in range(n):
        sensors.append({
            "sensor_id": f"sensor_{i+1:03d}",
            "p_bias": rng.normal(0, 0.3),       # psi bias (calibration offset)
            "q_bias": rng.normal(0, 0.2),        # lps bias
            "noise_pct": rng.uniform(0.02, 0.04),  # same range for ALL sensors
        })
    return sensors

# ici un capteur ne donne jamais la valeur parfaite
def _apply_sensor_model(value: float, bias: float, noise_pct: float,
                        base_value: float, age_years: int) -> float:
    #age_drift = (age_years / 30.0) * np.random.normal(0, 0.1)
    noise_std = base_value * noise_pct
    return value + bias  + np.random.normal(0, noise_std)



# micro-transients (applied to ALL scenarios uniformly)
def _maybe_add_transient(p: float, q: float, prob: float = 0.04) -> tuple[float, float]:
    if random.random() < prob:
        p += np.random.choice([-1, 1]) * np.random.uniform(0.8, 2.5)
        q += np.random.choice([-1, 1]) * np.random.uniform(0.3, 1.5)
    return p, q


# non-gaussian sensor artifacts (applied uniformly to ALL scenarios)
def _apply_sensor_artifacts(readings: list[dict]) -> list[dict]:
    n = len(readings)
    # Sensor sticking: 5% chance the sensor freezes for 2-3 consecutive readings
    if random.random() < 0.05:
        stick_start = random.randint(0, max(0, n - 3))
        stick_len = random.randint(2, 3)
        stuck_p = readings[stick_start]["pressure_psi"]
        stuck_q = readings[stick_start]["flow_rate_lps"]
        for j in range(stick_start, min(stick_start + stick_len, n)):
            readings[j]["pressure_psi"] = stuck_p
            readings[j]["flow_rate_lps"] = stuck_q
    # Spikes: each reading has a 3% chance of a sudden jump
    for i in range(n):
        if random.random() < 0.03:
            spike = np.random.uniform(3.0, 8.0) * np.random.choice([-1, 1])
            readings[i]["pressure_psi"] = max(0, readings[i]["pressure_psi"] + spike)
    return readings


# time-series generators
def _generate_normal_series(base_p: float, base_q: float, temp: float,
                            sensor: dict, age: int) -> list[dict]:
    readings = []
    drift_direction = np.random.normal(0, 0.03)  # slow demand drift per minute

    for i in range(WINDOW_SIZE):
        demand_drift = drift_direction * i
        p = _apply_sensor_model(
            base_p * (1 + demand_drift), sensor["p_bias"],
            sensor["noise_pct"], base_p, age)
        q = _apply_sensor_model(
            base_q * (1 + demand_drift * 0.7), sensor["q_bias"],
            sensor["noise_pct"], base_q, age)
        p, q = _maybe_add_transient(p, q)
        readings.append({
            "pressure_psi": max(0, p),
            "flow_rate_lps": max(0, q),
            "ambient_temp_c": temp + np.random.normal(0, 0.3),
        })
    return _apply_sensor_artifacts(readings)

def _generate_ambiguous_series(base_p: float, base_q: float, temp: float,
                               sensor: dict, age: int) -> list[dict]:
    readings = []

    scenario = random.choices(
        ["demand_shift", "pump_cycle", "valve_opening",
         "construction_vibration", "scheduled_purge", "meter_drift"],
        weights=[0.30, 0.12, 0.25, 0.11, 0.12, 0.10],
    )[0]

    for i in range(WINDOW_SIZE):
        if scenario == "demand_shift":
            shift = np.random.uniform(-0.20, -0.35) * (i / WINDOW_SIZE)
            p_raw = base_p * (1 + shift)
            q_raw = base_q * (1 + shift * np.random.uniform(0.6, 0.9))
        elif scenario == "pump_cycle":
            amp = np.random.uniform(1.2, 2.8)
            freq = np.random.uniform(0.8, 1.3)
            phase = np.random.uniform(0, 2 * math.pi)
            osc = amp * math.sin(freq * 2 * math.pi * i / WINDOW_SIZE + phase)
            p_raw = base_p + osc
            q_raw = base_q - osc * np.random.uniform(0.2, 0.5)
        elif scenario == "valve_opening":
            opening_rate = np.random.uniform(0.03, 0.10)
            stabilize = min(i / (WINDOW_SIZE * 0.6), 1.0)
            p_raw = base_p * (1 - opening_rate * stabilize)
            q_raw = base_q * (1 + opening_rate * 0.6 * stabilize)
        elif scenario == "construction_vibration":
            vib_amp = np.random.uniform(0.5, 2.0)
            irregular = np.random.normal(0, 0.5)
            osc = vib_amp * math.sin(3.0 * i + irregular) * np.random.uniform(0.6, 1.4)
            p_raw = base_p + osc
            q_raw = base_q + osc * np.random.uniform(0.3, 0.6)
        elif scenario == "scheduled_purge":
            purge_mid = WINDOW_SIZE // 2
            purge_half = 2
            if abs(i - purge_mid) <= purge_half:
                intensity = 1.0 - abs(i - purge_mid) / (purge_half + 0.1)
                drop = np.random.uniform(0.08, 0.20) * intensity
                p_raw = base_p * (1 - drop)
                q_raw = base_q * (1 + drop * 0.7)
            else:
                p_raw = base_p
                q_raw = base_q
        else:  # meter_drift
            drift_rate = np.random.uniform(0.005, 0.015) * np.random.choice([-1, 1])
            if i < int(WINDOW_SIZE * 0.7):
                p_raw = base_p * (1 + drift_rate * i)
                q_raw = base_q
            else:
                p_raw = base_p
                q_raw = base_q

        p = _apply_sensor_model(p_raw, sensor["p_bias"], sensor["noise_pct"], base_p, age)
        q = _apply_sensor_model(q_raw, sensor["q_bias"], sensor["noise_pct"], base_q, age)
        p, q = _maybe_add_transient(p, q)
        readings.append({
            "pressure_psi": max(0, p),
            "flow_rate_lps": max(0, q),
            "ambient_temp_c": temp + np.random.normal(0, 0.4),
        })
    return _apply_sensor_artifacts(readings)


def _leak_coefficient_growth(pressure_ratio: float, material: str) -> float:

    elasticity = PIPE_ELASTICITY.get(material, 0.05)
    return 1.0 + elasticity * max(0.0, 1.0 - pressure_ratio)


def _generate_leak_series(base_p: float, base_q: float, temp: float,
                          sensor: dict, age: int, severity: str,
                          diameter_mm: float, material: str) -> list[dict]:

    dynamic = random.choices(["abrupt", "incipient"], weights=[0.5, 0.5])[0]


    hole_area_fracs = {
        "minor":    np.random.uniform(0.001, 0.005),
        "moderate": np.random.uniform(0.005, 0.020),
        "severe":   np.random.uniform(0.020, 0.080),
    }
    final_area_frac = hole_area_fracs[severity]

    diameter_factor = math.sqrt(200.0 / max(diameter_mm, 50.0))


    compensation_prob = {"minor": 0.35, "moderate": 0.12, "severe": 0.03}[severity]
    if random.random() < compensation_prob:
        pressure_compensation = np.random.uniform(0.4, 0.85)
    else:
        pressure_compensation = 0.0

    onset = np.random.randint(0, WINDOW_SIZE // 3 + 1)

    peak_step = np.random.randint(onset + 1, WINDOW_SIZE + 1)

    readings = []
    for i in range(WINDOW_SIZE):
        if i < onset:
            p_raw = base_p
            q_raw = base_q
        else:
            if dynamic == "abrupt":
                area_frac = final_area_frac
            else:  # incipient: linear ramp of hole area, like LeakDB's
                   # leak_step_increment ramp of leak_diameter
                progress = min((i - onset) / max(peak_step - onset, 1), 1.0)
                area_frac = final_area_frac * progress

            # Effective orifice area translates into an equivalent pressure
            # ratio via a bounded, monotonic area -> pressure_ratio mapping
            # (not a claim about real hydraulic transients), scaled by
            # diameter_factor as before. Coefficient reduced from an earlier
            # value that let severe leaks on small pipes crush pressure_ratio
            # to ~0.01 within 1-2 steps, which made p_drop_pct wildly
            # unstable (division by a near-zero first reading) -- see
            # README.md for the diagnostic. 12.0 keeps pressure_ratio in a
            # more plausible 0.3-0.9 range across the severity bands.
            pressure_ratio = math.exp(-diameter_factor * area_frac * 12.0)
            growth = _leak_coefficient_growth(pressure_ratio, material)
            q_leak = base_q * area_frac * growth * math.sqrt(max(pressure_ratio, 0.01))
            q_raw = base_q + q_leak * np.random.uniform(8, 15)

            p_physical = base_p * pressure_ratio
            # observed pressure is partially masked by regulation; q_leak
            # above is computed from the true physical pressure_ratio, not
            # the masked one, so the leak itself is not weakened -- only
            # what the pressure sensor sees is.
            p_raw = p_physical + (base_p - p_physical) * pressure_compensation

        p = _apply_sensor_model(p_raw, sensor["p_bias"], sensor["noise_pct"], base_p, age)
        q = _apply_sensor_model(q_raw, sensor["q_bias"], sensor["noise_pct"], base_q, age)
        p, q = _maybe_add_transient(p, q)
        readings.append({
            "pressure_psi": max(0, p),
            "flow_rate_lps": max(0, q),
            "ambient_temp_c": temp + np.random.normal(0, 0.3),
        })
    return _apply_sensor_artifacts(readings)


# feature engineering
def compute_features(readings: list[dict]) -> dict:
    pressures = np.array([r["pressure_psi"] for r in readings])
    flows = np.array([r["flow_rate_lps"] for r in readings])
    temps = np.array([r["ambient_temp_c"] for r in readings])
    n = len(pressures)
    xs = np.arange(n, dtype=float)

    p_mean = float(np.mean(pressures))
    p_std = float(np.std(pressures))
    p_min = float(np.min(pressures))
    p_max = float(np.max(pressures))
    p_first = max(float(pressures[0]), 0.01)
    p_last = float(pressures[-1])
    p_drop_pct = (p_first - p_last) / p_first * 100.0
    p_slope = float(np.polyfit(xs, pressures, 1)[0]) if n >= 2 else 0.0
    p_rolling_std_5 = float(np.std(pressures[-5:])) if n >= 5 else p_std
    p_jitter = float(np.std(np.diff(pressures))) if n >= 2 else 0.0

    q_mean = float(np.mean(flows))
    q_std = float(np.std(flows))
    q_first = max(float(flows[0]), 0.01)
    q_last = float(flows[-1])
    q_surge_pct = (q_last - q_first) / q_first * 100.0
    q_slope = float(np.polyfit(xs, flows, 1)[0]) if n >= 2 else 0.0

    if p_std > 1e-6 and q_std > 1e-6:
        pq_corr = float(np.corrcoef(pressures, flows)[0, 1])
    else:
        pq_corr = 0.0

    t_mean = float(np.mean(temps))
    t_max = float(np.max(temps))
    zero_count = int(np.sum(pressures == 0.0))

    return {
        "p_mean": round(p_mean, 2), "p_std": round(p_std, 4),
        "p_min": round(p_min, 2), "p_max": round(p_max, 2),
        "p_drop_pct": round(p_drop_pct, 2), "p_slope": round(p_slope, 4),
        "p_rolling_std_5": round(p_rolling_std_5, 4), "p_jitter": round(p_jitter, 4),
        "q_mean": round(q_mean, 2), "q_std": round(q_std, 4),
        "q_surge_pct": round(q_surge_pct, 2), "q_slope": round(q_slope, 4),
        "pq_corr": round(pq_corr, 4),
        "t_mean": round(t_mean, 1), "t_max": round(t_max, 1),
        "zero_count": zero_count,
    }



def generate_dataset(n_samples: int = 10000, leak_ratio: float = 0.40,
                     seed: int = 42, ambiguous_ratio: float = 0.45) -> pd.DataFrame:
    np.random.seed(seed)
    random.seed(seed)

    sensor_pool = _build_sensor_pool(N_SENSORS, seed)
    n_leaks = int(n_samples * leak_ratio)
    n_normal = n_samples - n_leaks
    n_ambiguous = int(n_normal * ambiguous_ratio)
    n_clean = n_normal - n_ambiguous

    rows = []

    def _make_row(readings, pipe, sensor, age, hour, label):
        features = compute_features(readings)
        features.update({
            "sensor_id": sensor["sensor_id"],
            "pipe_diameter_mm": pipe["diameter_mm"],
            "pipe_age_years": age,
            "pipe_material": pipe["material"],
            "hour_of_day": hour,
            "leak": label,
        })
        rows.append(features)

    # Normal
    for _ in range(n_clean):
        pipe = _perturbed_pipe(random.choice(PIPE_CONFIGS))
        sensor = random.choice(sensor_pool)
        hour = np.random.randint(0, 24)
        day_of_week = np.random.randint(0, 7)
        age = np.random.randint(1, 30)
        temp = np.random.uniform(25.0, 55.0)
        demand_mult = _demand_multiplier(hour, day_of_week)
        base_p = pipe["nominal_psi"] * demand_mult
        base_q = pipe["nominal_flow"] * demand_mult
        readings = _generate_normal_series(base_p, base_q, temp, sensor, age)
        _make_row(readings, pipe, sensor, age, hour, 0)

    # Ambiguous (leak=0 but looks suspicious)
    for _ in range(n_ambiguous):
        pipe = _perturbed_pipe(random.choice(PIPE_CONFIGS))
        sensor = random.choice(sensor_pool)
        hour = np.random.randint(0, 24)
        day_of_week = np.random.randint(0, 7)
        age = np.random.randint(1, 30)
        temp = np.random.uniform(25.0, 55.0)
        demand_mult = _demand_multiplier(hour, day_of_week)
        base_p = pipe["nominal_psi"] * demand_mult
        base_q = pipe["nominal_flow"] * demand_mult
        readings = _generate_ambiguous_series(base_p, base_q, temp, sensor, age)
        _make_row(readings, pipe, sensor, age, hour, 0)

    # Leaks
    for _ in range(n_leaks):
        pipe = _perturbed_pipe(random.choice(PIPE_CONFIGS))
        sensor = random.choice(sensor_pool)
        hour = np.random.randint(0, 24)
        day_of_week = np.random.randint(0, 7)
        age = np.random.randint(1, 30)
        temp = np.random.uniform(25.0, 55.0)
        severity = np.random.choice(["minor", "moderate", "severe"], p=[0.50, 0.30, 0.20])
        demand_mult = _demand_multiplier(hour, day_of_week)
        base_p = pipe["nominal_psi"] * demand_mult
        base_q = pipe["nominal_flow"] * demand_mult
        readings = _generate_leak_series(base_p, base_q, temp, sensor, age,
                                         severity, pipe["diameter_mm"], pipe["material"])
        _make_row(readings, pipe, sensor, age, hour, 1)

    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="AquaPulse leak detection dataset generato")
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--leak-ratio", type=float, default=0.40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="leak_detection_dataset.csv")
    parser.add_argument("--ambiguous-ratio", type=float, default=0.45,
                        help="Fraction of non-leak samples drawn from ambiguous "
                             "(vs clean) scenarios. See generate_dataset() docstring.")
    args = parser.parse_args()

    print(f"Generating {args.samples} windows (leak ratio: {args.leak_ratio:.0%})...")
    df = generate_dataset(n_samples=args.samples, leak_ratio=args.leak_ratio,
                          seed=args.seed, ambiguous_ratio=args.ambiguous_ratio)

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    df.to_csv(output_path, index=False)

    print(f"\nSaved: {output_path}")
    print(f"Shape: {df.shape}")
    print(f"\nLabel distribution:")
    print(f"  Normal: {(df['leak']==0).sum()} ({(df['leak']==0).mean():.1%})")
    print(f"  Leak:   {(df['leak']==1).sum()} ({(df['leak']==1).mean():.1%})")
    print(f"\nLeak feature summary by material (mean p_drop_pct, q_surge_pct):")
    leak_df = df[df["leak"] == 1]
    print(leak_df.groupby("pipe_material")[["p_drop_pct", "q_surge_pct"]].mean().to_string())
    print(f"\nSensor distribution (top 5):")
    print(df["sensor_id"].value_counts().head().to_string())
    print(f"\nLeak rate per sensor (should be ~uniform):")
    sr = df.groupby("sensor_id")["leak"].mean()
    print(f"  min={sr.min():.2%}  max={sr.max():.2%}  std={sr.std():.4f}")


if __name__ == "__main__":
    main()