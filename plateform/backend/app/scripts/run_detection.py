"""Development detection runner. Never starts with FastAPI and never runs in tests."""

from __future__ import annotations

import argparse
import sys

from app.db.session import get_session_factory, reset_engine
from app.detection.engine import DetectionEngine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AquaPulse deterministic detection runner")
    parser.add_argument("--once", action="store_true", default=True, help="One bounded run (default)")
    parser.add_argument("--sensor", help="Limit to one sensor external ID")
    parser.add_argument("--all", action="store_true", help="Evaluate every sensor (default if --sensor omitted)")
    parser.add_argument("--window", type=int, help="Lookback window in minutes")
    parser.add_argument("--rule", help="Limit to one rule code")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate without writing detections")
    parser.add_argument("--explain", action="store_true", help="Print concise rule evidence")
    args = parser.parse_args(argv)

    reset_engine()
    session = get_session_factory()()
    try:
        engine = DetectionEngine(session)
        summary = engine.run(
            sensor_external_id=args.sensor,
            rule_code=args.rule,
            window_minutes=args.window,
            dry_run=args.dry_run,
            explain=args.explain,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Detection run failed: {exc}", file=sys.stderr)
        session.rollback()
        return 1
    finally:
        session.close()

    print("Detection run complete")
    print(f"  sensors checked: {summary.sensors_checked}")
    print(f"  rules evaluated: {summary.rules_evaluated}")
    print(f"  detections created: {summary.detections_created}")
    print(f"  detections deduplicated: {summary.detections_deduplicated}")
    print(f"  recovered: {summary.recovered}")
    print(f"  errors: {summary.errors}")
    print(f"  dry-run: {summary.dry_run}")
    if summary.created_numbers:
        print("  numbers: " + ", ".join(summary.created_numbers))
    if args.explain:
        for line in summary.explanations:
            print(f"  explain: {line}")
    for message in summary.error_messages:
        print(f"  error: {message}", file=sys.stderr)
    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
