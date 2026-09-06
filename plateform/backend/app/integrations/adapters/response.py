from datetime import datetime

from app.data.incidents import SEED_NOW
from app.integrations.constants import CONTRACT_VERSION
from app.integrations.contracts.response import (
    NetworkDeniedV1,
    NetworkGrantV1,
    OperatorContactV1,
    ResponseRequestV1,
    ResponseResultV1,
)


def to_response_request(
    *,
    run_id: str,
    incident_id: str,
    cluster_id: str,
    device_id: str,
    severity_tier: int,
    requested_at: datetime | None = None,
) -> ResponseRequestV1:
    clock = requested_at or SEED_NOW
    return ResponseRequestV1(
        schema_version=CONTRACT_VERSION,
        run_id=run_id,
        requested_at=clock,
        data_mode="simulated",
        incident_id=incident_id,
        cluster_id=cluster_id,
        device_id=device_id,
        severity_tier=severity_tier,
        network_grant=NetworkGrantV1(granted=False, data_mode="mock"),
        network_denied=NetworkDeniedV1(denied=True, reason="camara_disabled", data_mode="mock"),
        operator_contact=OperatorContactV1(display_name="Demo Operator", channel="unconfigured"),
    )


def parse_response_result(payload: dict) -> ResponseResultV1:
    return ResponseResultV1.model_validate(payload)
