"""Manual generator for due maintenance plans.

Does not start with FastAPI. Never starts or completes work.
Creates at most one open work order per due enabled plan cycle.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.data.incidents import SEED_NOW
from app.db.session import get_session_factory
from app.services.maintenance import MaintenanceService


def parse_as_of(value: str | None) -> datetime:
    if not value:
        return SEED_NOW
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def generate(*, as_of: datetime | None = None) -> dict[str, int]:
    when = as_of or SEED_NOW
    session = get_session_factory()()
    try:
        return MaintenanceService(session).generate_due_work_orders(as_of=when)
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create work orders for enabled due maintenance plans.")
    parser.add_argument(
        "--as-of",
        default="2026-09-01T07:45:00Z",
        help="ISO-8601 reference time. Defaults to the AquaPulse demo clock.",
    )
    args = parser.parse_args()
    result = generate(as_of=parse_as_of(args.as_of))
    print(
        f"Maintenance generator as_of={args.as_of}: "
        f"created={result['created']} skipped={result['skipped']} "
        f"errors={result['errors']} examined={result['examined']}"
    )


if __name__ == "__main__":
    main()
