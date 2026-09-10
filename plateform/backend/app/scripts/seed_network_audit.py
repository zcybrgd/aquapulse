"""Keep disabled agent integration registry rows. Do not seed dummy agent runs."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AgentAuditEvent
from app.db.models.integration import AgentIntegration, AgentRun
from app.integrations.constants import INVESTIGATION_AGENT, RESPONSE_AGENT
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT
from app.scripts.cleanup_dummy_agent_data import clear_dummy_agent_data, preview_dummy_agent_data


def _seed_network_agent(session: Session) -> AgentIntegration:
    row = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == NETWORK_AGENT_CODE))
    values = {
        "display_name": "Network Management Agent",
        "contract_version": NETWORK_CONTRACT,
        "enabled": False,
        "mode": "disabled",
        "health_status": "disabled",
        "base_url": None,
        "extra_metadata": {
            "seeded": True,
            "contract_status": "awaiting_team_confirmation",
            "note": "Network Agent is not part of this integration.",
        },
    }
    if row is None:
        row = AgentIntegration(agent_code=NETWORK_AGENT_CODE, **values)
        session.add(row)
        session.flush()
        return row
    for key, value in values.items():
        setattr(row, key, value)
    session.flush()
    return row


def seed_network_audit(session: Session) -> dict[str, int]:
    clear_dummy_agent_data(session)
    investigation = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == INVESTIGATION_AGENT))
    response = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == RESPONSE_AGENT))
    _seed_network_agent(session)
    if investigation is None or response is None:
        raise RuntimeError("Investigation and Response agent integrations must be seeded first")

    session.flush()
    remaining = preview_dummy_agent_data(session)
    mock_runs = int(session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.data_mode == MOCK_DATA_MODE)) or 0)
    mock_events = int(session.scalar(select(func.count()).select_from(AgentAuditEvent).where(AgentAuditEvent.data_mode == MOCK_DATA_MODE)) or 0)
    return {
        "observations": 0,
        "network_events": remaining.mock_network_agent_events,
        "runs": mock_runs,
        "events": mock_events,
        "findings": remaining.agent_findings,
        "recommendations": remaining.agent_response_recommendations,
    }
