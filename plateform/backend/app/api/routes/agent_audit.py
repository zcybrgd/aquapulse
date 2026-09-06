from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_agent_audit_service
from app.network.constants import MOCK_DATA_MODE
from app.schemas.agent_audit import (
    AgentAuditEventDetail,
    AgentAuditEventListResponse,
    AgentAuditRunDetail,
    AgentAuditRunListResponse,
    AgentAuditSummary,
)
from app.services.agent_audit import AgentAuditService

router = APIRouter(prefix="/agent-audit", tags=["agent-audit"])


@router.get("/summary", response_model=AgentAuditSummary)
def get_agent_audit_summary(
    agent_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    incident: str | None = Query(default=None),
    detection: str | None = Query(default=None),
    device: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    data_mode: str | None = Query(default=MOCK_DATA_MODE),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    service: AgentAuditService = Depends(get_agent_audit_service),
) -> AgentAuditSummary:
    return service.summary(
        agent_code=agent_code,
        status=status,
        decision=decision,
        incident=incident,
        detection=detection,
        device=device,
        cluster=cluster,
        data_mode=data_mode,
        start=start,
        end=end,
        search=search,
    )


@router.get("/runs", response_model=AgentAuditRunListResponse)
def list_agent_audit_runs(
    agent_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    incident: str | None = Query(default=None),
    detection: str | None = Query(default=None),
    device: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    data_mode: str | None = Query(default=MOCK_DATA_MODE),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: AgentAuditService = Depends(get_agent_audit_service),
) -> AgentAuditRunListResponse:
    return service.list_runs(
        page=page,
        page_size=page_size,
        agent_code=agent_code,
        status=status,
        decision=decision,
        incident=incident,
        detection=detection,
        device=device,
        cluster=cluster,
        data_mode=data_mode,
        start=start,
        end=end,
        search=search,
    )


@router.get("/runs/{run_id}", response_model=AgentAuditRunDetail)
def get_agent_audit_run(
    run_id: str,
    service: AgentAuditService = Depends(get_agent_audit_service),
) -> AgentAuditRunDetail:
    return service.get_run(run_id)


@router.get("/events", response_model=AgentAuditEventListResponse)
def list_agent_audit_events(
    agent_code: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    pipeline_stage: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    event_status: str | None = Query(default=None),
    incident: str | None = Query(default=None),
    detection: str | None = Query(default=None),
    device: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    data_mode: str | None = Query(default=MOCK_DATA_MODE),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    service: AgentAuditService = Depends(get_agent_audit_service),
) -> AgentAuditEventListResponse:
    return service.list_events(
        page=page,
        page_size=page_size,
        agent_code=agent_code,
        run_id=run_id,
        pipeline_stage=pipeline_stage,
        event_type=event_type,
        event_status=event_status,
        incident=incident,
        detection=detection,
        device=device,
        cluster=cluster,
        data_mode=data_mode,
        start=start,
        end=end,
        search=search,
    )


@router.get("/events/{event_id}", response_model=AgentAuditEventDetail)
def get_agent_audit_event(
    event_id: str,
    service: AgentAuditService = Depends(get_agent_audit_service),
) -> AgentAuditEventDetail:
    return service.get_event(event_id)
