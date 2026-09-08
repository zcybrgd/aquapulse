"""Remove dummy agent operational rows from the development database.

Does not drop integration tables or disable ingest endpoints.
"""

from __future__ import annotations

from app.db.session import get_session_factory
from app.scripts.seed_integrations import seed_integrations
from app.scripts.seed_network_audit import clear_dummy_agent_data, seed_network_audit


def main() -> None:
    session = get_session_factory()()
    try:
        seed_integrations(session)
        removed = clear_dummy_agent_data(session)
        counts = seed_network_audit(session)
        session.commit()
        print("Cleared dummy agent operational data")
        print(f"  deleted dummy runs: {removed['deleted_runs']}")
        print(f"  remaining mock runs: {counts['runs']}")
        print(f"  remaining mock audit events: {counts['events']}")
        print(f"  findings: {counts['findings']}")
        print(f"  recommendations: {counts['recommendations']}")
        print(f"  network agent events: {counts['network_events']}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
