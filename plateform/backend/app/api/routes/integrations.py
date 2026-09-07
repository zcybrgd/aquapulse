from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.api.deps import get_integration_service
from app.integrations.contracts.investigation import AgentHealth
from app.schemas.integrations import (
    AgentFindingRecord,
    AgentIngestAccepted,
    AgentIntegrationDetail,
    AgentReadiness,
    AgentRecommendationRecord,
    AgentRunDetail,
    AgentRunSummary,
    AgentSummary,
    ContractMetadata,
    ValidationResult,
)
from app.services.integrations import IntegrationService

router = APIRouter(prefix="/integrations/agents", tags=["integrations"])


@router.get("/readiness", response_model=AgentReadiness)
def get_readiness(service: IntegrationService = Depends(get_integration_service)) -> AgentReadiness:
    return service.readiness()


@router.get("/contracts/investigation/v1", response_model=ContractMetadata)
def investigation_contract(service: IntegrationService = Depends(get_integration_service)) -> ContractMetadata:
    return service.contract_metadata("investigation")


@router.get("/contracts/response/v1", response_model=ContractMetadata)
def response_contract(service: IntegrationService = Depends(get_integration_service)) -> ContractMetadata:
    return service.contract_metadata("response")


@router.post("/contracts/investigation/v1/validate-request", response_model=ValidationResult)
def validate_investigation_request(
    payload: dict,
    service: IntegrationService = Depends(get_integration_service),
) -> ValidationResult:
    return service.validate_investigation_request(payload)


@router.post("/contracts/investigation/v1/validate-response", response_model=ValidationResult)
def validate_investigation_response(
    payload: dict,
    service: IntegrationService = Depends(get_integration_service),
) -> ValidationResult:
    return service.validate_investigation_response(payload)


@router.post("/contracts/response/v1/validate-request", response_model=ValidationResult)
def validate_response_request(
    payload: dict,
    service: IntegrationService = Depends(get_integration_service),
) -> ValidationResult:
    return service.validate_response_request(payload)


@router.post("/contracts/response/v1/validate-response", response_model=ValidationResult)
def validate_response_result(
    payload: dict,
    service: IntegrationService = Depends(get_integration_service),
) -> ValidationResult:
    return service.validate_response_result(payload)


@router.get("/runs", response_model=list[AgentRunSummary])
def list_runs(
    agent_type: str | None = None,
    service: IntegrationService = Depends(get_integration_service),
) -> list[AgentRunSummary]:
    return service.list_runs(agent_type)


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
def get_run(run_id: str, service: IntegrationService = Depends(get_integration_service)) -> AgentRunDetail:
    return service.get_run(run_id)


@router.get("/findings", response_model=list[AgentFindingRecord])
def list_findings(service: IntegrationService = Depends(get_integration_service)) -> list[AgentFindingRecord]:
    return service.list_findings()


@router.get("/findings/{finding_id}", response_model=AgentFindingRecord)
def get_finding(
    finding_id: UUID,
    service: IntegrationService = Depends(get_integration_service),
) -> AgentFindingRecord:
    return service.get_finding(finding_id)


@router.get("/recommendations", response_model=list[AgentRecommendationRecord])
def list_recommendations(
    service: IntegrationService = Depends(get_integration_service),
) -> list[AgentRecommendationRecord]:
    return service.list_recommendations()


@router.get("/recommendations/{recommendation_id}", response_model=AgentRecommendationRecord)
def get_recommendation(
    recommendation_id: UUID,
    service: IntegrationService = Depends(get_integration_service),
) -> AgentRecommendationRecord:
    return service.get_recommendation(recommendation_id)


@router.post("/investigation/v1/results", response_model=AgentIngestAccepted, status_code=202)
def ingest_investigation_results(
    payload: dict,
    service: IntegrationService = Depends(get_integration_service),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> AgentIngestAccepted:
    return service.accept_investigation_result(payload, idempotency_key=x_idempotency_key)


@router.post("/response/v1/results", response_model=AgentIngestAccepted, status_code=202)
def ingest_response_results(
    payload: dict,
    service: IntegrationService = Depends(get_integration_service),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> AgentIngestAccepted:
    return service.accept_response_result(payload, idempotency_key=x_idempotency_key)


@router.get("", response_model=list[AgentSummary])
def list_agents(service: IntegrationService = Depends(get_integration_service)) -> list[AgentSummary]:
    return service.list_agents()


@router.get("/{agent_code}", response_model=AgentIntegrationDetail)
def get_agent(agent_code: str, service: IntegrationService = Depends(get_integration_service)) -> AgentIntegrationDetail:
    return service.get_agent(agent_code)


@router.get("/{agent_code}/health", response_model=AgentHealth)
def agent_health(agent_code: str, service: IntegrationService = Depends(get_integration_service)) -> AgentHealth:
    return service.health(agent_code)


@router.post("/{agent_code}/execute")
def execute_agent(agent_code: str, service: IntegrationService = Depends(get_integration_service)) -> None:
    _ = agent_code
    service.refuse_execution()
