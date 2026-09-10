"""Remove dummy agent operational rows from a development database.

Dry-run by default. Pass --confirm to delete. Refuses production.
Does not drop integration tables, contracts, or ingest endpoints.
Never prints secrets or complete raw payloads.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import AgentAuditEvent
from app.db.models.integration import (
    AgentFinding,
    AgentResponseRecommendation,
    AgentRun,
    IntegrationIdentityMapping,
)
from app.db.session import get_session_factory
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE

HISTORICAL_MOCK_RUN_IDS = (
    "AGRUN-000201",
    "AGRUN-000202",
    "AGRUN-000203",
    "AGRUN-000204",
    "AGRUN-000205",
)

DEMO_ID_PREFIXES = (
    "cluster-desert-",
    "seg-neom-",
    "valve-neom-",
)

PRODUCTION_ENVS = {"production", "prod"}


@dataclass
class CleanupCounts:
    agent_audit_events: int = 0
    agent_response_recommendations: int = 0
    agent_findings: int = 0
    agent_runs: int = 0
    mock_network_agent_events: int = 0
    dummy_identity_mappings: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "agent_audit_events": self.agent_audit_events,
            "agent_response_recommendations": self.agent_response_recommendations,
            "agent_findings": self.agent_findings,
            "agent_runs": self.agent_runs,
            "mock_network_agent_events": self.mock_network_agent_events,
            "dummy_identity_mappings": self.dummy_identity_mappings,
        }


@dataclass
class DummySelection:
    run_ids: list[UUID] = field(default_factory=list)
    event_ids: list[UUID] = field(default_factory=list)
    finding_ids: list[UUID] = field(default_factory=list)
    recommendation_ids: list[UUID] = field(default_factory=list)
    mapping_ids: list[UUID] = field(default_factory=list)
    network_event_ids: list[UUID] = field(default_factory=list)


def _demo_id_filters(*columns):
    clauses = []
    for column in columns:
        for prefix in DEMO_ID_PREFIXES:
            clauses.append(column.like(f"{prefix}%"))
    return or_(*clauses) if clauses else None


def _is_production(settings: Settings) -> bool:
    return settings.app_env.strip().lower() in PRODUCTION_ENVS


def refuse_production(settings: Settings | None = None) -> None:
    current = settings or get_settings()
    if _is_production(current):
        raise SystemExit("Refusing to run dummy-agent cleanup against a production environment.")


def table_totals(session: Session) -> CleanupCounts:
    network_events = int(
        session.scalar(
            select(func.count())
            .select_from(AgentAuditEvent)
            .where(
                (AgentAuditEvent.agent_code == NETWORK_AGENT_CODE)
                | (AgentAuditEvent.pipeline_stage == "network_management"),
                AgentAuditEvent.data_mode == MOCK_DATA_MODE,
            )
        )
        or 0
    )
    dummy_mappings = int(
        session.scalar(
            select(func.count())
            .select_from(IntegrationIdentityMapping)
            .where(_demo_id_filters(IntegrationIdentityMapping.internal_public_id))
        )
        or 0
    )
    return CleanupCounts(
        agent_audit_events=int(session.scalar(select(func.count()).select_from(AgentAuditEvent)) or 0),
        agent_response_recommendations=int(
            session.scalar(select(func.count()).select_from(AgentResponseRecommendation)) or 0
        ),
        agent_findings=int(session.scalar(select(func.count()).select_from(AgentFinding)) or 0),
        agent_runs=int(session.scalar(select(func.count()).select_from(AgentRun)) or 0),
        mock_network_agent_events=network_events,
        dummy_identity_mappings=dummy_mappings,
    )


def select_dummy_agent_data(session: Session) -> DummySelection:
    finding_run_ids = list(
        session.scalars(
            select(AgentFinding.agent_run_id).where(
                _demo_id_filters(
                    AgentFinding.external_cluster_id,
                    AgentFinding.external_segment_id,
                    AgentFinding.external_valve_id,
                )
            )
        ).all()
    )
    recommendation_run_ids = list(
        session.scalars(
            select(AgentResponseRecommendation.agent_run_id).where(
                _demo_id_filters(
                    AgentResponseRecommendation.external_cluster_id,
                    AgentResponseRecommendation.external_device_id,
                )
            )
        ).all()
    )
    run_filters = [
        AgentRun.public_id.in_(HISTORICAL_MOCK_RUN_IDS),
        AgentRun.data_mode == MOCK_DATA_MODE,
        AgentRun.agent_type == NETWORK_AGENT_CODE,
    ]
    linked_run_ids = finding_run_ids + recommendation_run_ids
    if linked_run_ids:
        run_filters.append(AgentRun.id.in_(linked_run_ids))
    run_ids = list(session.scalars(select(AgentRun.id).where(or_(*run_filters))).all())

    event_filters = [
        AgentAuditEvent.data_mode == MOCK_DATA_MODE,
        AgentAuditEvent.public_id.like("AAE-%"),
        AgentAuditEvent.public_id.like("NETEVT-%"),
        AgentAuditEvent.agent_code == NETWORK_AGENT_CODE,
        _demo_id_filters(AgentAuditEvent.external_cluster_id, AgentAuditEvent.external_device_id),
    ]
    if run_ids:
        event_filters.append(AgentAuditEvent.agent_run_id.in_(run_ids))
    event_ids = list(session.scalars(select(AgentAuditEvent.id).where(or_(*event_filters))).all())

    network_event_ids = list(
        session.scalars(
            select(AgentAuditEvent.id).where(
                AgentAuditEvent.id.in_(event_ids) if event_ids else AgentAuditEvent.id.is_(None),
                or_(
                    AgentAuditEvent.agent_code == NETWORK_AGENT_CODE,
                    AgentAuditEvent.pipeline_stage == "network_management",
                ),
            )
        ).all()
    )

    finding_filters = [
        _demo_id_filters(
            AgentFinding.external_cluster_id,
            AgentFinding.external_segment_id,
            AgentFinding.external_valve_id,
        )
    ]
    if run_ids:
        finding_filters.append(AgentFinding.agent_run_id.in_(run_ids))
    finding_ids = list(session.scalars(select(AgentFinding.id).where(or_(*finding_filters))).all())

    recommendation_filters = [
        _demo_id_filters(
            AgentResponseRecommendation.external_cluster_id,
            AgentResponseRecommendation.external_device_id,
        )
    ]
    if run_ids:
        recommendation_filters.append(AgentResponseRecommendation.agent_run_id.in_(run_ids))
    recommendation_ids = list(
        session.scalars(select(AgentResponseRecommendation.id).where(or_(*recommendation_filters))).all()
    )
    mapping_ids = list(
        session.scalars(
            select(IntegrationIdentityMapping.id).where(
                _demo_id_filters(IntegrationIdentityMapping.internal_public_id)
            )
        ).all()
    )
    return DummySelection(
        run_ids=run_ids,
        event_ids=event_ids,
        finding_ids=finding_ids,
        recommendation_ids=recommendation_ids,
        mapping_ids=mapping_ids,
        network_event_ids=network_event_ids,
    )


def preview_dummy_agent_data(session: Session) -> CleanupCounts:
    selected = select_dummy_agent_data(session)
    return CleanupCounts(
        agent_audit_events=len(selected.event_ids),
        agent_response_recommendations=len(selected.recommendation_ids),
        agent_findings=len(selected.finding_ids),
        agent_runs=len(selected.run_ids),
        mock_network_agent_events=len(selected.network_event_ids),
        dummy_identity_mappings=len(selected.mapping_ids),
    )


def delete_dummy_agent_data(session: Session) -> CleanupCounts:
    selected = select_dummy_agent_data(session)
    deleted = CleanupCounts(
        mock_network_agent_events=len(selected.network_event_ids),
        dummy_identity_mappings=len(selected.mapping_ids),
    )
    if selected.event_ids:
        deleted.agent_audit_events = session.execute(
            delete(AgentAuditEvent).where(AgentAuditEvent.id.in_(selected.event_ids))
        ).rowcount or 0
    if selected.recommendation_ids:
        deleted.agent_response_recommendations = session.execute(
            delete(AgentResponseRecommendation).where(AgentResponseRecommendation.id.in_(selected.recommendation_ids))
        ).rowcount or 0
    if selected.finding_ids:
        deleted.agent_findings = session.execute(
            delete(AgentFinding).where(AgentFinding.id.in_(selected.finding_ids))
        ).rowcount or 0
    if selected.run_ids:
        deleted.agent_runs = session.execute(delete(AgentRun).where(AgentRun.id.in_(selected.run_ids))).rowcount or 0
    if selected.mapping_ids:
        session.execute(
            delete(IntegrationIdentityMapping).where(IntegrationIdentityMapping.id.in_(selected.mapping_ids))
        )
    session.flush()
    return deleted


def clear_dummy_agent_data(session: Session) -> dict[str, int]:
    deleted = delete_dummy_agent_data(session)
    return {"deleted_runs": deleted.agent_runs, **deleted.as_dict()}


def _print_counts(title: str, counts: CleanupCounts) -> None:
    print(title)
    for key, value in counts.as_dict().items():
        print(f"  {key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove dummy Investigation/Response/Network Agent runtime rows.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Delete selected dummy records. Without this flag the command is a dry-run.",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    refuse_production(settings)

    session = get_session_factory()()
    try:
        before = table_totals(session)
        selected = preview_dummy_agent_data(session)
        print(f"Environment: {settings.app_env}")
        _print_counts("Current table totals", before)
        _print_counts("Dummy records selected", selected)
        if not args.confirm:
            print("Dry-run only. Re-run with --confirm to delete the selected dummy records.")
            return 0

        deleted = delete_dummy_agent_data(session)
        session.commit()
        after = table_totals(session)
        _print_counts("Deleted", deleted)
        _print_counts("Final table totals", after)
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
