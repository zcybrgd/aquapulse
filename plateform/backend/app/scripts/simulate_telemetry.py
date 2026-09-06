"""Development-only simulator. Never starts with FastAPI and never runs in tests."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.session import get_session_factory, reset_engine
from app.schemas.telemetry import IngestReading
from app.services.telemetry import TelemetryService
from app.services.telemetry_patterns import SCENARIOS, scenario_reading_values, simulator_source_id


def _refuse_if_disabled(explicit: bool) -> int | None:
    settings = get_settings()
    if settings.app_env == "production" and not explicit:
        print("Simulator refused: production environment requires an explicit --enable flag.", file=sys.stderr)
        return 2
    enabled = explicit or settings.telemetry_simulator_enabled
    if not enabled:
        print(
            "Simulator refused: set TELEMETRY_SIMULATOR_ENABLED=true or pass --enable.",
            file=sys.stderr,
        )
        return 2
    return None


def simulate_once(
    *,
    sensor_id: str | None = None,
    scenario: str = "normal",
    step: int = 0,
    total_steps: int = 1,
    when: datetime | None = None,
) -> list[str]:
    session = get_session_factory()()
    try:
        service = TelemetryService(session)
        sensors = service.repository.list_sensors()
        if sensor_id:
            sensors = [item for item in sensors if item.external_id == sensor_id]
            if not sensors:
                raise SystemExit(f"Sensor {sensor_id} was not found.")
        now = (when or datetime.now(timezone.utc)).replace(microsecond=0)
        lines: list[str] = []
        for sensor in sensors:
            if sensor.operational_status == "offline" and scenario == "normal":
                lines.append(f"skip {sensor.external_id} (offline)")
                continue
            values = scenario_reading_values(
                sensor.external_id,
                now,
                sensor.operational_status,
                scenario=scenario,
                step=step,
                total_steps=total_steps,
            )
            if values is None:
                lines.append(f"skip {sensor.external_id} (missing_telemetry scenario; no rows deleted)")
                continue
            result = service.ingest(
                IngestReading(
                    sensor_external_id=sensor.external_id,
                    time=now,
                    source_message_id=simulator_source_id(sensor.external_id, now),
                    received_at=now,
                    raw_payload={
                        "origin": "simulator",
                        "data_mode": "simulated",
                        "scenario": scenario,
                        "step": step,
                    },
                    **values,
                )
            )
            lines.append(f"{result.status} {result.sensor_id} {result.time.isoformat()} scenario={scenario}")
        return lines
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AquaPulse development telemetry simulator")
    parser.add_argument("--once", action="store_true", help="Insert one cycle and exit")
    parser.add_argument("--sensor", help="Limit to one sensor external ID")
    parser.add_argument("--interval", type=float, help="Seconds between live cycles")
    parser.add_argument("--count", type=int, default=0, help="Number of cycles (0 = until Ctrl+C unless --once)")
    parser.add_argument("--enable", action="store_true", help="Override TELEMETRY_SIMULATOR_ENABLED=false")
    parser.add_argument(
        "--scenario",
        default="normal",
        choices=SCENARIOS,
        help="Explicit scenario. Default is normal. Does not run detection.",
    )
    parser.add_argument(
        "--spacing-minutes",
        type=float,
        default=3.0,
        help="Minutes between batch points when --count is used with a scenario",
    )
    args = parser.parse_args(argv)

    get_settings.cache_clear()
    reset_engine()
    refused = _refuse_if_disabled(args.enable)
    if refused is not None:
        return refused

    settings = get_settings()
    interval = args.interval if args.interval is not None else settings.telemetry_simulator_interval_seconds
    interval = max(0.5, interval / max(settings.telemetry_simulator_speed, 0.1))

    batch_count = 1 if args.once else args.count
    if batch_count and args.scenario != "normal":
        end = datetime.now(timezone.utc).replace(microsecond=0)
        spacing = timedelta(minutes=max(0.1, args.spacing_minutes))
        executed = 0
        for step in range(batch_count):
            when = end - spacing * (batch_count - 1 - step)
            lines = simulate_once(
                sensor_id=args.sensor,
                scenario=args.scenario,
                step=step,
                total_steps=batch_count,
                when=when,
            )
            executed += 1
            print(f"cycle {executed} utc={when.isoformat()} scenario={args.scenario}")
            for line in lines:
                print(f"  {line}")
        print("Detection was not run. Use python -m app.scripts.run_detection explicitly.")
        return 0

    cycles = 1 if args.once else args.count
    executed = 0
    try:
        while True:
            lines = simulate_once(
                sensor_id=args.sensor,
                scenario=args.scenario,
                step=executed,
                total_steps=max(cycles, 1),
            )
            executed += 1
            print(f"cycle {executed} utc={datetime.now(timezone.utc).isoformat()} scenario={args.scenario}")
            for line in lines:
                print(f"  {line}")
            if args.once or (cycles and executed >= cycles):
                if args.scenario != "normal":
                    print("Detection was not run. Use python -m app.scripts.run_detection explicitly.")
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
