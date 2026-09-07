"""Clear dummy Investigation, Response, and Network Agent operational rows.

Keeps disabled agent integration registry rows so ingest endpoints stay ready.
Does not create mock runs, findings, recommendations, or audit events.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import AgentAuditEvent
from app.db.models.integration import (
    AgentFinding,
    AgentIntegration,
    AgentResponseRecommendation,
    AgentRun,
)
from app.integrations.constants import INVESTIGATION_AGENT, RESPONSE_AGENT
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT

HISTORICAL_MOCK_RUN_IDS = (
    "AGRUN-000201",
    "AGRUN-000202",
    "AGRUN-000203",
    "AGRUN-000204",
    "AGRUN-000205",
)


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


def clear_dummy_agent_data(session: Session) -> dict[str, int]:
    dummy_run_ids = list(
        session.scalars(
            select(AgentRun.id).where(
                (AgentRun.public_id.in_(HISTORICAL_MOCK_RUN_IDS))
                | (AgentRun.data_mode == MOCK_DATA_MODE)
                | (AgentRun.agent_type == NETWORK_AGENT_CODE)
            )
        ).all()
    )
    deleted_runs = 0
    if dummy_run_ids:
        session.execute(delete(AgentAuditEvent).where(AgentAuditEvent.agent_run_id.in_(dummy_run_ids)))
        session.execute(delete(AgentFinding).where(AgentFinding.agent_run_id.in_(dummy_run_ids)))
        session.execute(
            delete(AgentResponseRecommendation).where(AgentResponseRecommendation.agent_run_id.in_(dummy_run_ids))
        )
        deleted_runs = session.execute(delete(AgentRun).where(AgentRun.id.in_(dummy_run_ids))).rowcount or 0
    session.execute(delete(AgentAuditEvent).where(AgentAuditEvent.public_id.like("AAE-%")))
    session.execute(delete(AgentAuditEvent).where(AgentAuditEvent.data_mode == MOCK_DATA_MODE))
    session.flush()
    return {"deleted_runs": int(deleted_runs)}


def seed_network_audit(session: Session) -> dict[str, int]:
    clear_dummy_agent_data(session)
    investigation = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == INVESTIGATION_AGENT))
    response = session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == RESPONSE_AGENT))
    _seed_network_agent(session)
    if investigation is None or response is None:
        raise RuntimeError("Investigation and Response agent integrations must be seeded first")

    session.flush()
    mock_runs = int(session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.data_mode == MOCK_DATA_MODE)) or 0)
    mock_events = int(session.scalar(select(func.count()).select_from(AgentAuditEvent).where(AgentAuditEvent.data_mode == MOCK_DATA_MODE)) or 0)
    return {
        "observations": 0,
        "network_events": 0,
        "runs": mock_runs,
        "events": mock_events,
        "findings": 0,
        "recommendations": 0,
    }
