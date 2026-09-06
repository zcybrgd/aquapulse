from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.network.constants import MOCK_DATA_MODE


class NetworkEventSummary(BaseModel):
    id: str
    public_id: str
    event_id: str
    event_type: str
    status: str
    summary: str
    cluster_id: str | None
    device_id: str | None
    incident_id: str | None
    occurred_at: datetime
    data_mode: str = MOCK_DATA_MODE
    contract_version: str


class NetworkEventDetail(NetworkEventSummary):
    payload: dict[str, Any]
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    error_code: str | None
    error_message: str | None


class NetworkEventListResponse(BaseModel):
    items: list[NetworkEventSummary]
    total: int
    page: int
    page_size: int
    data_mode: str = MOCK_DATA_MODE
    note: str = "Mock Network Agent logs — final contract pending"


class NetworkSummary(BaseModel):
    connectivity_checks: int
    grants: int
    denials: int
    releases: int
    errors: int
    latest_event_at: datetime | None
    data_mode: str = MOCK_DATA_MODE
    contract_status: str = "Awaiting confirmation"
    note: str = "Mock Network Agent logs — final contract pending"
    reference_time: datetime
