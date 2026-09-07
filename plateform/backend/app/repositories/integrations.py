from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.network.constants import MOCK_DATA_MODE
from app.db.models.integration import (
    AgentFinding,
    AgentIntegration,
    AgentResponseRecommendation,
    AgentRun,
    IntegrationIdentityMapping,
)


class IntegrationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_integrations(self) -> list[AgentIntegration]:
        return list(self.session.scalars(select(AgentIntegration).order_by(AgentIntegration.agent_code)).all())

    def get_integration(self, agent_code: str) -> AgentIntegration | None:
        return self.session.scalar(select(AgentIntegration).where(AgentIntegration.agent_code == agent_code))

    def next_run_public_id(self) -> str:
        existing = list(self.session.scalars(select(AgentRun.public_id)).all())
        highest = 0
        for public_id in existing:
            suffix = public_id.rsplit("-", 1)[-1]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"AGRUN-{highest + 1:06d}"

    def get_run(self, public_id: str) -> AgentRun | None:
        return self.session.scalar(select(AgentRun).where(AgentRun.public_id == public_id))

    def get_run_by_idempotency(self, key: str) -> AgentRun | None:
        return self.session.scalar(select(AgentRun).where(AgentRun.idempotency_key == key).order_by(AgentRun.created_at.asc()))

    def list_runs(self, *, agent_type: str | None = None, include_mock: bool = False) -> list[AgentRun]:
        stmt = select(AgentRun).order_by(AgentRun.created_at.desc())
        if agent_type:
            stmt = stmt.where(AgentRun.agent_type == agent_type)
        if not include_mock:
            stmt = stmt.where(AgentRun.data_mode != MOCK_DATA_MODE)
        return list(self.session.scalars(stmt.limit(100)).all())

    def add_run(self, run: AgentRun) -> None:
        self.session.add(run)

    def get_finding(self, finding_id: UUID) -> AgentFinding | None:
        return self.session.get(AgentFinding, finding_id)

    def get_finding_by_anomaly(self, provider: str, anomaly_id: str) -> AgentFinding | None:
        return self.session.scalar(
            select(AgentFinding).where(
                AgentFinding.provider == provider,
                AgentFinding.external_anomaly_id == anomaly_id,
            )
        )

    def list_findings(self, *, include_mock: bool = False) -> list[AgentFinding]:
        stmt = (
            select(AgentFinding)
            .options(joinedload(AgentFinding.run))
            .join(AgentRun, AgentFinding.agent_run_id == AgentRun.id)
            .order_by(AgentFinding.created_at.desc())
            .limit(200)
        )
        if not include_mock:
            stmt = stmt.where(AgentRun.data_mode != MOCK_DATA_MODE)
        return list(self.session.scalars(stmt).unique().all())

    def unmapped_finding_count(self) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(AgentFinding)
                .join(AgentRun, AgentFinding.agent_run_id == AgentRun.id)
                .where(AgentFinding.mapping_status != "mapped", AgentRun.data_mode != MOCK_DATA_MODE)
            )
            or 0
        )

    def add_finding(self, finding: AgentFinding) -> None:
        self.session.add(finding)

    def get_recommendation(self, rec_id: UUID) -> AgentResponseRecommendation | None:
        return self.session.get(AgentResponseRecommendation, rec_id)

    def get_recommendation_by_result(self, provider: str, result_id: str) -> AgentResponseRecommendation | None:
        return self.session.scalar(
            select(AgentResponseRecommendation).where(
                AgentResponseRecommendation.provider == provider,
                AgentResponseRecommendation.external_result_id == result_id,
            )
        )

    def list_recommendations(self, *, include_mock: bool = False) -> list[AgentResponseRecommendation]:
        stmt = (
            select(AgentResponseRecommendation)
            .join(AgentRun, AgentResponseRecommendation.agent_run_id == AgentRun.id)
            .order_by(AgentResponseRecommendation.created_at.desc())
            .limit(200)
        )
        if not include_mock:
            stmt = stmt.where(AgentRun.data_mode != MOCK_DATA_MODE)
        return list(self.session.scalars(stmt).all())

    def add_recommendation(self, recommendation: AgentResponseRecommendation) -> None:
        self.session.add(recommendation)

    def mapping_count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(IntegrationIdentityMapping).where(IntegrationIdentityMapping.enabled.is_(True))) or 0)


class IdentityMappingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, provider: str, entity_type: str, external_id: str) -> IntegrationIdentityMapping | None:
        return self.session.scalar(
            select(IntegrationIdentityMapping).where(
                IntegrationIdentityMapping.provider == provider,
                IntegrationIdentityMapping.entity_type == entity_type,
                IntegrationIdentityMapping.external_id == external_id,
            )
        )

    def upsert(self, mapping: IntegrationIdentityMapping) -> IntegrationIdentityMapping:
        existing = self.get(mapping.provider, mapping.entity_type, mapping.external_id)
        if existing is None:
            self.session.add(mapping)
            self.session.flush()
            return mapping
        existing.internal_entity_type = mapping.internal_entity_type
        existing.internal_public_id = mapping.internal_public_id
        existing.enabled = mapping.enabled
        existing.extra_metadata = mapping.extra_metadata
        return existing

    def list_all(self) -> list[IntegrationIdentityMapping]:
        return list(self.session.scalars(select(IntegrationIdentityMapping).order_by(IntegrationIdentityMapping.provider)).all())
