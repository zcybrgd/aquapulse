"""Idempotent seed for disabled agent integrations. Does not create identity mappings."""

from sqlalchemy.orm import Session

from app.db.models.integration import AgentIntegration
from app.integrations.constants import CONTRACT_VERSION, INVESTIGATION_AGENT, RESPONSE_AGENT
from app.repositories.integrations import IntegrationRepository


AGENTS = (
    (INVESTIGATION_AGENT, "Investigation Agent"),
    (RESPONSE_AGENT, "Response Agent"),
)


def seed_integrations(session: Session) -> int:
    repo = IntegrationRepository(session)
    for code, name in AGENTS:
        row = repo.get_integration(code)
        if row is None:
            session.add(
                AgentIntegration(
                    agent_code=code,
                    display_name=name,
                    contract_version=CONTRACT_VERSION,
                    enabled=False,
                    mode="disabled",
                    health_status="disabled",
                    extra_metadata={"seeded": True},
                )
            )
        else:
            row.display_name = name
            row.contract_version = CONTRACT_VERSION
            row.enabled = False
            row.mode = "disabled"
            if row.health_status not in {"unknown", "disabled", "healthy", "unhealthy", "unreachable"}:
                row.health_status = "disabled"
    session.flush()
    return len(AGENTS)
