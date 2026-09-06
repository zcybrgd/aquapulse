from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NetworkEventNotFoundError
from app.data.incidents import SEED_NOW
from app.db.models import AgentAuditEvent
from app.integrations.sanitize import sanitize_payload
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE, NETWORK_CONTRACT
from app.repositories.agent_audit import AgentAuditRepository
from app.schemas.network_health import (
    NetworkEventDetail,
    NetworkEventListResponse,
    NetworkEventSummary,
    NetworkSummary,
)


def _event_id(event: AgentAuditEvent) -> str:
    payload = event.output_summary or {}
    value = payload.get("event_id")
    return str(value) if value else event.public_id


class NetworkHealthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AgentAuditRepository(session)

    def _to_summary(self, event: AgentAuditEvent) -> NetworkEventSummary:
        payload = event.output_summary or {}
        return NetworkEventSummary(
            id=str(event.id),
            public_id=event.public_id,
            event_id=_event_id(event),
            event_type=event.event_type,
            status=event.status,
            summary=event.summary,
            cluster_id=event.external_cluster_id or payload.get("cluster_id"),
            device_id=event.external_device_id or payload.get("device_id"),
            incident_id=event.incident_public_id or payload.get("incident_id"),
            occurred_at=event.occurred_at,
            data_mode=event.data_mode,
            contract_version=event.contract_version,
        )

    def _query(self, **filters) -> list[AgentAuditEvent]:
        return self.repository.list_events(
            agent_code=NETWORK_AGENT_CODE,
            pipeline_stage="network_management",
            event_type=filters.get("event_type"),
            event_status=filters.get("status"),
            incident=filters.get("incident"),
            device=filters.get("device"),
            cluster=filters.get("cluster"),
            start=filters.get("start"),
            end=filters.get("end"),
            search=filters.get("search"),
            data_mode=MOCK_DATA_MODE,
        )

    def summary(self, **filters) -> NetworkSummary:
        events = self._query(**filters)
        latest = max((event.occurred_at for event in events), default=None)
        return NetworkSummary(
            connectivity_checks=sum(1 for event in events if event.event_type == "connectivity_check"),
            grants=sum(1 for event in events if event.event_type == "qod_granted"),
            denials=sum(1 for event in events if event.event_type == "qod_denied"),
            releases=sum(1 for event in events if event.event_type == "qod_released"),
            errors=sum(1 for event in events if event.event_type == "agent_error"),
            latest_event_at=latest,
            data_mode=MOCK_DATA_MODE,
            contract_status="Awaiting confirmation",
            reference_time=SEED_NOW,
        )

    def list_events(self, *, page: int = 1, page_size: int = 25, **filters) -> NetworkEventListResponse:
        events = list(reversed(self._query(**filters)))
        total = len(events)
        start = max(0, (page - 1) * page_size)
        page_rows = events[start : start + page_size]
        return NetworkEventListResponse(
            items=[self._to_summary(event) for event in page_rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_event(self, event_id: str) -> NetworkEventDetail:
        event = self.repository.get_event(event_id)
        if event is None or event.pipeline_stage != "network_management":
            raise NetworkEventNotFoundError(event_id)
        summary = self._to_summary(event)
        payload = sanitize_payload(event.output_summary or {})
        return NetworkEventDetail(
            **summary.model_dump(),
            payload=payload,
            input_summary=sanitize_payload(event.input_summary or {}),
            output_summary=payload,
            error_code=event.error_code,
            error_message=event.error_message,
        )
