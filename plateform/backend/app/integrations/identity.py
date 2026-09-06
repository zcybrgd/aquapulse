from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.integration import IntegrationIdentityMapping
from app.integrations.constants import INVESTIGATION_AGENT, RESPONSE_AGENT
from app.repositories.integrations import IdentityMappingRepository


@dataclass
class MappingLookup:
    external_id: str
    entity_type: str
    internal_public_id: str | None
    mapped: bool
    warning: dict | None = None


class IdentityMapper:
    """Never guess. Unknown external IDs stay unmapped."""

    def __init__(self, session: Session, *, provider: str) -> None:
        self.repository = IdentityMappingRepository(session)
        self.provider = provider

    def resolve(self, entity_type: str, external_id: str | None) -> MappingLookup:
        if not external_id:
            return MappingLookup("", entity_type, None, False, None)
        row = self.repository.get(self.provider, entity_type, external_id)
        if row is None or not row.enabled:
            return MappingLookup(
                external_id,
                entity_type,
                None,
                False,
                {
                    "code": "agent_identity_unmapped",
                    "entity_type": entity_type,
                    "external_id": external_id,
                    "message": "No configured mapping exists for this external identity.",
                },
            )
        return MappingLookup(external_id, entity_type, row.internal_public_id, True, None)


def investigation_mapper(session: Session) -> IdentityMapper:
    return IdentityMapper(session, provider=INVESTIGATION_AGENT)


def response_mapper(session: Session) -> IdentityMapper:
    return IdentityMapper(session, provider=RESPONSE_AGENT)


def mapping_record(row: IntegrationIdentityMapping) -> dict:
    return {
        "provider": row.provider,
        "entity_type": row.entity_type,
        "external_id": row.external_id,
        "internal_entity_type": row.internal_entity_type,
        "internal_public_id": row.internal_public_id,
        "enabled": row.enabled,
    }
