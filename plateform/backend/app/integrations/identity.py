from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.integration import AgentFinding, AgentResponseRecommendation, AgentRun, IntegrationIdentityMapping
from app.integrations.constants import INVESTIGATION_AGENT, RESPONSE_AGENT
from app.repositories.integrations import IdentityMappingRepository


@dataclass
class MappingLookup:
    external_id: str
    entity_type: str
    internal_public_id: str | None
    mapped: bool
    warning: dict | None = None


class IdentityMapper:
    """Never guess. Unknown external IDs stay unmapped."""

    def __init__(self, session: Session, *, provider: str) -> None:
        self.repository = IdentityMappingRepository(session)
        self.provider = provider

    def resolve(self, entity_type: str, external_id: str | None) -> MappingLookup:
        if not external_id:
            return MappingLookup("", entity_type, None, False, None)
        row = self.repository.get(self.provider, entity_type, external_id)
        if row is None or not row.enabled:
            return MappingLookup(
                external_id,
                entity_type,
                None,
                False,
                {
                    "code": "agent_identity_unmapped",
                    "entity_type": entity_type,
                    "external_id": external_id,
                    "message": "No configured mapping exists for this external identity.",
                },
            )
        return MappingLookup(external_id, entity_type, row.internal_public_id, True, None)


def investigation_mapper(session: Session) -> IdentityMapper:
    return IdentityMapper(session, provider=INVESTIGATION_AGENT)


def response_mapper(session: Session) -> IdentityMapper:
    return IdentityMapper(session, provider=RESPONSE_AGENT)


def mapping_record(row: IntegrationIdentityMapping) -> dict:
    return {
        "provider": row.provider,
        "entity_type": row.entity_type,
        "external_id": row.external_id,
        "internal_entity_type": row.internal_entity_type,
        "internal_public_id": row.internal_public_id,
        "enabled": row.enabled,
    }


def _finding_status(cluster: MappingLookup, segment: MappingLookup, valve: MappingLookup, detection_mapped: bool) -> str:
    present = [item for item in (cluster.internal_public_id, segment.internal_public_id, valve.internal_public_id) if item]
    if present and len(present) == 3:
        return "mapped"
    if present or detection_mapped:
        return "partial"
    return "unmapped"


def apply_stored_mappings(session: Session) -> dict[str, int]:
    """Re-apply configured mappings onto already ingested findings and recommendations."""
    inv = investigation_mapper(session)
    resp = response_mapper(session)
    findings_updated = 0
    recommendations_updated = 0
    run_ids: set = set()

    for finding in session.scalars(select(AgentFinding)).all():
        cluster = inv.resolve("sensor_cluster", finding.external_cluster_id)
        segment = inv.resolve("segment", finding.external_segment_id)
        valve = inv.resolve("valve", finding.external_valve_id)
        detection = inv.resolve("detection", finding.external_anomaly_id)
        detection_mapped = bool(detection.mapped or finding.mapped_detection_id)
        status = _finding_status(cluster, segment, valve, detection_mapped)
        changed = (
            finding.mapped_sensor_id != cluster.internal_public_id
            or finding.mapped_segment_id != segment.internal_public_id
            or finding.mapped_valve_id != valve.internal_public_id
            or finding.mapping_status != status
        )
        if detection.mapped and finding.mapped_detection_id != detection.internal_public_id:
            finding.mapped_detection_id = detection.internal_public_id
            changed = True
        if not changed:
            continue
        finding.mapped_sensor_id = cluster.internal_public_id
        finding.mapped_segment_id = segment.internal_public_id
        finding.mapped_valve_id = valve.internal_public_id
        finding.mapping_status = status
        findings_updated += 1
        run_ids.add(finding.agent_run_id)

    for rec in session.scalars(select(AgentResponseRecommendation)).all():
        device = resp.resolve("device", rec.external_device_id)
        if not device.mapped:
            device = resp.resolve("valve", rec.external_device_id)
        incident = resp.resolve("incident", rec.external_incident_id)
        changed = rec.mapped_device_id != device.internal_public_id or rec.mapped_incident_number != incident.internal_public_id
        if not changed:
            continue
        rec.mapped_device_id = device.internal_public_id
        rec.mapped_incident_number = incident.internal_public_id
        recommendations_updated += 1
        run_ids.add(rec.agent_run_id)

    for run_id in run_ids:
        run = session.get(AgentRun, run_id)
        if run is None:
            continue
        warnings: list[dict] = []
        if run.agent_type == INVESTIGATION_AGENT:
            mapper = inv
            for finding in run.findings:
                for lookup in (
                    mapper.resolve("sensor_cluster", finding.external_cluster_id),
                    mapper.resolve("segment", finding.external_segment_id),
                    mapper.resolve("valve", finding.external_valve_id),
                    mapper.resolve("detection", finding.external_anomaly_id),
                ):
                    if lookup.warning and not (lookup.entity_type == "detection" and finding.mapped_detection_id):
                        warnings.append(lookup.warning)
        elif run.agent_type == RESPONSE_AGENT:
            mapper = resp
            for rec in run.recommendations:
                device = mapper.resolve("device", rec.external_device_id)
                if not device.mapped:
                    device = mapper.resolve("valve", rec.external_device_id)
                for lookup in (
                    mapper.resolve("sensor_cluster", rec.external_cluster_id),
                    device,
                    mapper.resolve("incident", rec.external_incident_id),
                ):
                    if lookup.warning:
                        warnings.append(lookup.warning)
        run.mapping_warnings = warnings

    return {"findings": findings_updated, "recommendations": recommendations_updated}
