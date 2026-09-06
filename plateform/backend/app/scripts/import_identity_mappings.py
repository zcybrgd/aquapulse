"""Import identity mappings from JSON. Never guesses missing rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.models.integration import IntegrationIdentityMapping
from app.db.session import get_session_factory
from app.integrations.constants import ENTITY_TYPES
from app.repositories.integrations import IdentityMappingRepository


def import_mappings(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("Mapping file must be a JSON array.")
    session = get_session_factory()()
    repo = IdentityMappingRepository(session)
    count = 0
    try:
        for item in payload:
            if item.get("entity_type") not in ENTITY_TYPES:
                raise SystemExit(f"Unsupported entity_type: {item.get('entity_type')}")
            if item.get("internal_entity_type") not in ENTITY_TYPES:
                raise SystemExit(f"Unsupported internal_entity_type: {item.get('internal_entity_type')}")
            repo.upsert(
                IntegrationIdentityMapping(
                    provider=item["provider"],
                    entity_type=item["entity_type"],
                    external_id=item["external_id"],
                    internal_entity_type=item["internal_entity_type"],
                    internal_public_id=item["internal_public_id"],
                    enabled=bool(item.get("enabled", True)),
                    extra_metadata=item.get("metadata") or {},
                )
            )
            count += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import AquaPulse agent identity mappings.")
    parser.add_argument("--file", required=True, help="JSON array of mapping objects")
    args = parser.parse_args()
    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"File not found: {path}")
    count = import_mappings(path)
    print(f"Imported {count} identity mapping(s). Unknown IDs are never guessed.")


if __name__ == "__main__":
    main()
