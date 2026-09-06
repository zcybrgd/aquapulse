from datetime import datetime, timezone

from app.data.incidents import SEED_NOW
from app.integrations.constants import CONTRACT_VERSION
from app.integrations.contracts.investigation import (
    InvestigationBatchRequestV1,
    InvestigationClusterV1,
    InvestigationRequestV1,
    InvestigationResponseV1,
    OptionalMetric,
)
from app.schemas.detections import InvestigationAgentInputV1


def optional_from_values(values: list[float], unit: str | None) -> OptionalMetric:
    if not values:
        return OptionalMetric(available=False, unit=unit)
    return OptionalMetric(value=values[-1], values=values, unit=unit, available=True)


def evidence_values(payload: InvestigationAgentInputV1, metric_prefix: str) -> list[float]:
    found: list[float] = []
    for item in payload.structured_evidence:
        if item.metric.startswith(metric_prefix) or metric_prefix in item.metric:
            found.append(item.observed_value)
    return found


def to_investigation_request(
    inputs: list[InvestigationAgentInputV1],
    *,
    run_id: str,
    batch_id: str,
    requested_at: datetime | None = None,
) -> InvestigationRequestV1:
    """Adapt AquaPulse InvestigationAgentInputV1 rows into the friend batch contract."""
    clock = requested_at or SEED_NOW
    clusters: list[InvestigationClusterV1] = []
    for item in inputs:
        pressure_values = evidence_values(item, "pressure")
        flow_values = evidence_values(item, "flow")
        temperature_values = evidence_values(item, "temperature")
        population = item.population_served
        clusters.append(
            InvestigationClusterV1(
                cluster_id=f"AP-CLUSTER-{item.detection_id}",
                external_aliases=[],
                segment_id=item.pipeline_context.segment_id,
                sensor_ids=[item.sensor.id],
                telemetry_window={
                    "start": item.telemetry_window.start,
                    "end": item.telemetry_window.end,
                },
                pressure=optional_from_values(pressure_values, "kPa"),
                flow=optional_from_values(flow_values, "L/s"),
                data_freshness=item.network_metadata.telemetry_freshness,
                network_context={
                    "zone": item.network_metadata.zone,
                    "signal_strength_dbm": item.network_metadata.signal_strength_dbm,
                    "packet_loss_pct": item.network_metadata.packet_loss_pct,
                    "latest_reading_at": (
                        item.network_metadata.latest_reading_at.isoformat()
                        if item.network_metadata.latest_reading_at
                        else None
                    ),
                },
                temperature=optional_from_values(temperature_values, "°C"),
                criticality=item.criticality,
                population_served=population,
                associated_valve_id=None,
                pipe_diameter_mm=None,
                pipe_diameter_available=False,
                population_available=population is not None,
                data_mode=item.data_mode,
            )
        )
    return InvestigationRequestV1(
        schema_version=CONTRACT_VERSION,
        run_id=run_id,
        requested_at=clock,
        data_mode="simulated",
        batch=InvestigationBatchRequestV1(
            batch_id=batch_id,
            analysis_timestamp=clock,
            clusters=clusters,
        ),
    )


def parse_investigation_response(payload: dict, *, run_id: str | None = None) -> InvestigationResponseV1:
    if "batch" in payload:
        model = InvestigationResponseV1.model_validate(payload)
    else:
        model = InvestigationResponseV1(
            schema_version=payload.get("schema_version", CONTRACT_VERSION),
            run_id=run_id,
            data_mode=payload.get("data_mode", "simulated"),
            batch=payload,
        )
    if run_id and model.run_id is None:
        model = model.model_copy(update={"run_id": run_id})
    return model


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
