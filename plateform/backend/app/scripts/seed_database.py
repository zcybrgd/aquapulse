"""Idempotent development seed for incidents, assets and demonstration map geometry."""

from __future__ import annotations

from dataclasses import dataclass

from geoalchemy2.shape import from_shape
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.assets.connectivity import normalize_device_msisdn, normalize_location_label
from app.data.assets import get_asset_catalog
from app.data.geometries import asset_point, segment_linestring, zone_multipolygon
from app.data.incidents import get_incidents, get_timeline
from app.db.models import (
    Asset,
    DetectionRule,
    Incident,
    IncidentTelemetry,
    IncidentTimelineEvent,
    Organization,
    PipelineSegment,
    SensorReading,
    Zone,
)
from app.db.models.maintenance import MaintenancePlan, MaintenanceWorkOrder
from app.db.session import get_session_factory
from app.schemas.incidents import IncidentDetail
from app.scripts.seed_integrations import seed_integrations
from app.scripts.seed_maintenance import seed_maintenance_demo
from app.scripts.seed_device_network import seed_device_network
from app.scripts.seed_network_audit import seed_network_audit
from app.scripts.seed_investigation import seed_investigation_demo
from app.scripts.seed_operations import seed_operations_demo
from app.scripts.seed_rules import seed_detection_rules
from app.scripts.seed_telemetry import seed_sensor_readings

ORG_SLUG = "aquapulse-demo"
ORG_NAME = "AquaPulse Demo Utility"
ORG_TIMEZONE = "Asia/Dubai"

ZONE_CATALOG: dict[str, dict[str, str]] = {
    "Corniche DMA": {"code": "CRN", "country": "United Arab Emirates", "region": "Abu Dhabi"},
    "Dubai Harbour": {"code": "HBR", "country": "United Arab Emirates", "region": "Dubai"},
    "Al Ain North": {"code": "AIN", "country": "United Arab Emirates", "region": "Al Ain"},
    "Jeddah North": {"code": "JED", "country": "Saudi Arabia", "region": "Jeddah"},
    "Doha West": {"code": "DOH", "country": "Qatar", "region": "Doha"},
    "Muscat Old Town": {"code": "MCT", "country": "Oman", "region": "Muscat"},
    "Casablanca Medina": {"code": "CAS", "country": "Morocco", "region": "Casablanca"},
    "Riyadh Industrial": {"code": "RUH", "country": "Saudi Arabia", "region": "Riyadh"},
    "Amman Heights": {"code": "AMM", "country": "Jordan", "region": "Amman"},
}

SEGMENT_CATALOG: dict[str, dict[str, object]] = {
    "Corniche Trunk Main · KM 4.2": {
        "external_id": "CRN-TRUNK-4.2",
        "upstream_node": "Corniche Inlet",
        "downstream_node": "KM 4.2 interceptor",
        "criticality_score": 3,
        "status": "operational",
    },
    "Harbour Transfer Main · Segment 7": {
        "external_id": "HBR-XFER-7",
        "upstream_node": "Harbour pump station",
        "downstream_node": "Segment 7",
        "criticality_score": 3,
        "status": "operational",
    },
    "Al Ain Feeder 3": {
        "external_id": "AIN-FEED-3",
        "upstream_node": "Al Ain North reservoir",
        "downstream_node": "Feeder chamber 3",
        "criticality_score": 2,
        "status": "operational",
    },
    "Obhur Feeder · Node 12": {
        "external_id": "JED-OBHUR-12",
        "upstream_node": "Jeddah North trunk",
        "downstream_node": "Node 12",
        "criticality_score": 2,
        "status": "operational",
    },
    "Lusail Distributor 2": {
        "external_id": "DOH-LUS-2",
        "upstream_node": "Lusail DMA inlet",
        "downstream_node": "Distributor 2",
        "criticality_score": 2,
        "status": "operational",
    },
    "Mutrah Distributor": {
        "external_id": "MCT-MUTRAH",
        "upstream_node": "Mutrah tank",
        "downstream_node": "Old Town mesh",
        "criticality_score": 1,
        "status": "operational",
    },
    "Medina Ring Main · Arc B": {
        "external_id": "CAS-RING-B",
        "upstream_node": "Arc A junction",
        "downstream_node": "Arc C junction",
        "criticality_score": 2,
        "status": "operational",
    },
    "Second Industrial Ring": {
        "external_id": "RUH-IND-2",
        "upstream_node": "Industrial inlet",
        "downstream_node": "Process-water loop",
        "criticality_score": 1,
        "status": "operational",
    },
    "Abdali Trunk": {
        "external_id": "AMM-ABDALI",
        "upstream_node": "Abdali reservoir",
        "downstream_node": "Heights DMA",
        "criticality_score": 2,
        "status": "operational",
    },
}

@dataclass
class SeedSummary:
    organization: str
    zones: int
    pipeline_segments: int
    assets: int
    incidents: int
    telemetry_points: int
    timeline_events: int
    sensor_readings: int
    detection_rules: int
    maintenance_plans: int
    maintenance_work_orders: int
    network_events: int
    device_network_snapshots: int
    agent_audit_events: int
    mock_agent_runs: int
    investigation_findings: int


def _get_or_create(session: Session, model, lookup: dict, values: dict):
    instance = session.scalar(select(model).filter_by(**lookup))
    if instance is None:
        instance = model(**lookup, **values)
        session.add(instance)
        session.flush()
        return instance
    for key, value in values.items():
        setattr(instance, key, value)
    return instance


def _percent_change(delta: float, base: float) -> float:
    if base == 0:
        return 0.0
    return round((delta / base) * 100, 4)


def _upsert_asset(
    session: Session,
    *,
    organization: Organization,
    zones: dict[str, Zone],
    segments: dict[str, PipelineSegment],
    source: dict,
) -> Asset:
    zone_name = str(source["zone"])
    if zone_name not in zones:
        raise RuntimeError(f"asset_zone_not_found: seed asset {source['external_id']} zone {zone_name!r}")
    zone = zones[zone_name]
    segment = segments[str(source["segment"])]
    if segment.zone_id != zone.id:
        raise RuntimeError(
            f"asset_zone_segment_mismatch: {source['external_id']} zone {zone.name} "
            f"does not match segment {segment.name}"
        )
    location_label = normalize_location_label(str(source.get("location_label") or ""))
    if location_label is None:
        raise RuntimeError(f"Seed asset {source['external_id']} is missing location_label")

    existing = session.scalar(
        select(Asset).filter_by(organization_id=organization.id, external_id=source["external_id"])
    )
    keep_msisdn = bool(
        existing is not None
        and existing.device_msisdn
        and not (existing.extra_metadata or {}).get("demo_msisdn")
    )
    incoming_msisdn = normalize_device_msisdn(source.get("device_msisdn"))

    asset = _get_or_create(
        session,
        Asset,
        {"organization_id": organization.id, "external_id": source["external_id"]},
        {
            "zone_id": zone.id,
            "pipeline_segment_id": segment.id,
            "name": source["name"],
            "asset_type": source["asset_type"],
            "operational_status": source["operational_status"],
            "last_seen_at": source["last_seen_at"],
            "manufacturer": source["manufacturer"],
            "model": source["model"],
            "serial_number": source["serial_number"],
            "firmware_version": source["firmware_version"],
            "installed_at": source["installed_at"],
            "commissioned_at": source["commissioned_at"],
            "latitude": source["latitude"],
            "longitude": source["longitude"],
            "battery_pct": source["battery_pct"],
            "signal_strength_dbm": source["signal_strength_dbm"],
            "sampling_interval_seconds": source["sampling_interval_seconds"],
            "last_maintenance_at": source["last_maintenance_at"],
            "next_maintenance_at": source["next_maintenance_at"],
            "control_mode": source["control_mode"],
            "current_position": source["current_position"],
            "health_score": source["health_score"],
            "location_label": location_label,
            "extra_metadata": source["extra_metadata"],
            "location": from_shape(
                asset_point(float(source["longitude"]), float(source["latitude"])),
                srid=4326,
            ),
        },
    )
    if asset.zone_id is None:
        raise RuntimeError(f"asset_zone_required: {asset.external_id} has no direct zone after seed")
    if keep_msisdn:
        return asset
    asset.device_msisdn = incoming_msisdn
    meta = dict(asset.extra_metadata or {})
    if incoming_msisdn:
        meta["demo_msisdn"] = True
    else:
        meta.pop("demo_msisdn", None)
    asset.extra_metadata = meta
    return asset


def _require_asset(session: Session, organization: Organization, external_id: str) -> Asset:
    asset = session.scalar(
        select(Asset).filter_by(organization_id=organization.id, external_id=external_id)
    )
    if asset is None:
        raise RuntimeError(f"Seed catalog is missing asset {external_id}")
    return asset


def _upsert_incident(
    session: Session,
    *,
    organization: Organization,
    zones: dict[str, Zone],
    segments: dict[str, PipelineSegment],
    source: IncidentDetail,
) -> Incident:
    zone = zones[source.zone]
    segment = segments[source.pipeline_segment]
    sensor = _require_asset(session, organization, source.sensor)
    valve = _require_asset(session, organization, source.associated_valve)
    base_pressure = source.telemetry[0].pressure if source.telemetry else 0.0
    base_flow = source.telemetry[0].flow_rate if source.telemetry else 0.0
    values = {
        "organization_id": organization.id,
        "zone_id": zone.id,
        "pipeline_segment_id": segment.id,
        "sensor_id": sensor.id,
        "valve_id": valve.id,
        "title": source.title,
        "classification": source.classification.value,
        "severity_tier": int(source.severity.value.split("_")[1]),
        "confidence": round(source.confidence / 100, 4),
        "status": source.status.value,
        "latitude": source.latitude,
        "longitude": source.longitude,
        "detected_at": source.detected_at,
        "updated_at": source.updated_at,
        "estimated_water_loss_m3": source.estimated_water_loss_m3,
        "estimated_loss_lps": round(source.estimated_water_loss_m3 / 3.6, 4),
        "population_affected": source.population_affected,
        "current_summary": source.current_summary,
        "pressure_change_pct": _percent_change(source.pressure_change_bar, base_pressure),
        "flow_change_pct": _percent_change(source.flow_change_m3h, base_flow),
        "network_condition": source.network_condition,
        "signal_strength_dbm": source.signal_strength_dbm,
        "packet_loss_pct": source.packet_loss_percent,
        "assigned_operator": source.assigned_operator,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "response_started_at": None,
        "resolved_at": source.updated_at if source.status.value == "resolved" else None,
        "resolved_by": (
            source.assigned_operator or "Seed Operator"
            if source.status.value == "resolved"
            else None
        ),
        "resolution_code": (
            "false_alarm"
            if source.incident_number == "INC-1837"
            else "other"
            if source.status.value == "resolved"
            else None
        ),
        "resolution_summary": (
            source.current_summary if source.status.value == "resolved" else None
        ),
        "agent_investigation_summary": source.agent_investigation_summary,
        "recommended_action": source.recommended_action,
        "evidence": [item.model_dump() for item in source.evidence],
        "network_details": {
            "device_reachability": source.device_reachability,
            "network_priority_status": source.network_priority_status,
            "pressure_change_bar": source.pressure_change_bar,
            "flow_change_m3h": source.flow_change_m3h,
        },
    }
    incident = _get_or_create(session, Incident, {"incident_number": source.incident_number}, values)
    session.execute(delete(IncidentTelemetry).where(IncidentTelemetry.incident_id == incident.id))
    session.execute(delete(IncidentTimelineEvent).where(IncidentTimelineEvent.incident_id == incident.id))
    session.flush()

    for point in source.telemetry:
        session.add(
            IncidentTelemetry(
                incident_id=incident.id,
                timestamp=point.timestamp,
                pressure=point.pressure,
                flow_rate=point.flow_rate,
                packet_loss_pct=point.packet_loss,
                is_detection_point=point.is_detection,
            )
        )

    events = get_timeline(source.incident_number) or []
    for event in events:
        session.add(
            IncidentTimelineEvent(
                incident_id=incident.id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                title=event.title,
                description=event.description,
                source=event.source.value,
                status=event.status,
                extra_metadata={"public_id": event.id},
            )
        )
    incident.updated_at = source.updated_at
    return incident


def seed_database(session: Session | None = None) -> SeedSummary:
    own_session = session is None
    db = get_session_factory()() if own_session else session
    assert db is not None
    try:
        organization = _get_or_create(
            db,
            Organization,
            {"slug": ORG_SLUG},
            {
                "name": ORG_NAME,
                "timezone": ORG_TIMEZONE,
            },
        )
        settings = dict(organization.settings or {})
        settings["demo"] = True
        settings["seed_version"] = "step-13-no-dummy-agents"
        organization.settings = settings

        zones: dict[str, Zone] = {}
        for name, meta in ZONE_CATALOG.items():
            zones[name] = _get_or_create(
                db,
                Zone,
                {"organization_id": organization.id, "code": meta["code"]},
                {
                    "name": name,
                    "country": meta["country"],
                    "region": meta["region"],
                    "boundary": from_shape(zone_multipolygon(name), srid=4326),
                },
            )

        segments: dict[str, PipelineSegment] = {}
        for name, meta in SEGMENT_CATALOG.items():
            zone_name = next(
                incident.zone for incident in get_incidents() if incident.pipeline_segment == name
            )
            population = next(
                (
                    incident.population_affected
                    for incident in get_incidents()
                    if incident.pipeline_segment == name
                ),
                0,
            )
            segments[name] = _get_or_create(
                db,
                PipelineSegment,
                {"organization_id": organization.id, "external_id": str(meta["external_id"])},
                {
                    "zone_id": zones[zone_name].id,
                    "name": name,
                    "upstream_node": str(meta["upstream_node"]),
                    "downstream_node": str(meta["downstream_node"]),
                    "criticality_score": int(meta["criticality_score"]),
                    "population_served": population,
                    "status": str(meta["status"]),
                    "extra_metadata": {"demo": True, "geometry_source": "seeded_demo"},
                    "geometry": from_shape(segment_linestring(name), srid=4326),
                },
            )

        catalog = get_incidents()
        for source in get_asset_catalog():
            _upsert_asset(
                db,
                organization=organization,
                zones=zones,
                segments=segments,
                source=source,
            )
        unzoned = db.scalars(select(Asset.external_id).where(Asset.zone_id.is_(None))).all()
        if unzoned:
            raise RuntimeError(f"asset_zone_required: {', '.join(unzoned)}")

        for source in catalog:
            _upsert_incident(
                db,
                organization=organization,
                zones=zones,
                segments=segments,
                source=source,
            )

        seed_sensor_readings(db, commit=False)
        seed_detection_rules(db, organization=organization)
        seed_investigation_demo(db)
        seed_operations_demo(db)
        seed_integrations(db)
        seed_maintenance_demo(db)
        network_audit = seed_network_audit(db)
        device_network = seed_device_network(db)

        db.commit()
        summary = SeedSummary(
            organization=organization.name,
            zones=db.scalar(select(func.count()).select_from(Zone).where(Zone.organization_id == organization.id)) or 0,
            pipeline_segments=db.scalar(
                select(func.count()).select_from(PipelineSegment).where(PipelineSegment.organization_id == organization.id)
            )
            or 0,
            assets=db.scalar(select(func.count()).select_from(Asset).where(Asset.organization_id == organization.id)) or 0,
            incidents=db.scalar(select(func.count()).select_from(Incident).where(Incident.organization_id == organization.id))
            or 0,
            telemetry_points=db.scalar(select(func.count()).select_from(IncidentTelemetry)) or 0,
            timeline_events=db.scalar(select(func.count()).select_from(IncidentTimelineEvent)) or 0,
            sensor_readings=db.scalar(select(func.count()).select_from(SensorReading)) or 0,
            detection_rules=db.scalar(
                select(func.count()).select_from(DetectionRule).where(DetectionRule.organization_id == organization.id)
            )
            or 0,
            maintenance_plans=db.scalar(select(func.count()).select_from(MaintenancePlan)) or 0,
            maintenance_work_orders=db.scalar(select(func.count()).select_from(MaintenanceWorkOrder)) or 0,
            network_events=network_audit.get("network_events", 0),
            device_network_snapshots=device_network["snapshots"],
            agent_audit_events=network_audit["events"],
            mock_agent_runs=network_audit["runs"],
            investigation_findings=network_audit.get("findings", 0),
        )
        return summary
    except Exception:
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()


def print_summary(summary: SeedSummary) -> None:
    print(f"Seeded {summary.organization}")
    print(f"  zones: {summary.zones}")
    print(f"  pipeline segments: {summary.pipeline_segments}")
    print(f"  assets: {summary.assets}")
    print(f"  incidents: {summary.incidents}")
    print(f"  telemetry points: {summary.telemetry_points}")
    print(f"  sensor readings: {summary.sensor_readings}")
    print(f"  detection rules: {summary.detection_rules}")
    print(f"  timeline events: {summary.timeline_events}")
    print(f"  maintenance plans: {summary.maintenance_plans}")
    print(f"  maintenance work orders: {summary.maintenance_work_orders}")
    print(f"  dummy agent runs: {summary.mock_agent_runs}")
    print(f"  investigation findings: {summary.investigation_findings}")
    print(f"  network agent events: {summary.network_events}")
    print(f"  device network snapshots: {summary.device_network_snapshots}")
    print(f"  agent audit events: {summary.agent_audit_events}")


def main() -> None:
    print_summary(seed_database())


if __name__ == "__main__":
    main()
