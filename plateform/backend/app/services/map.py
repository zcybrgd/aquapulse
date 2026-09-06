import json
from datetime import datetime, timezone

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm import Session

from app.assets.connectivity import mask_device_msisdn, public_zone_id
from app.core.exceptions import DatabaseUnavailableError
from app.db.models import Asset, Incident
from app.db.models.sensor_reading import SensorReading
from app.repositories.detections import DetectionRepository
from app.repositories.map import MapRepository
from app.repositories.telemetry import TelemetryRepository
from app.schemas.assets import AssetType, OperationalStatus
from app.schemas.incidents import Classification, IncidentStatus, SeverityTier
from app.schemas.map import (
    AssetFeatureProperties,
    DetectionFeatureProperties,
    FeatureCollection,
    GeoJSONGeometry,
    IncidentFeatureProperties,
    MapFeature,
    MapSummary,
    NearbyItem,
    NearbyResponse,
    PipelineFeatureProperties,
    ZoneFeatureProperties,
)
from app.services.incidents import ACTIVE_STATUSES
from app.services.telemetry import classify_freshness


def _geometry(raw: str | None) -> GeoJSONGeometry:
    if not raw:
        raise ValueError("Missing geometry")
    payload = json.loads(raw)
    return GeoJSONGeometry(type=payload["type"], coordinates=payload["coordinates"])


def _severity(tier: int) -> SeverityTier:
    return SeverityTier(f"tier_{tier}")


def _is_status(feature: MapFeature, status: OperationalStatus) -> bool:
    return (
        isinstance(feature.properties, AssetFeatureProperties)
        and feature.properties.operational_status == status
    )


def _is_active_incident(feature: MapFeature) -> bool:
    return (
        isinstance(feature.properties, IncidentFeatureProperties)
        and feature.properties.status.value in ACTIVE_STATUSES
    )


def _is_critical(feature: MapFeature) -> bool:
    return (
        isinstance(feature.properties, IncidentFeatureProperties)
        and feature.properties.severity == SeverityTier.tier_3
    )


class MapService:
    def __init__(self, session: Session) -> None:
        self.repository = MapRepository(session)
        self.telemetry = TelemetryRepository(session)
        self.detections_repository = DetectionRepository(session)

    def zones(self, *, zone: str | None = None) -> FeatureCollection:
        try:
            rows = self.repository.list_zones(zone=zone)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        features = [
            MapFeature(
                id=item.code,
                geometry=_geometry(geojson),
                properties=ZoneFeatureProperties(
                    code=item.code,
                    name=item.name,
                    country=item.country,
                    region=item.region,
                    asset_count=int(asset_count or 0),
                    active_incident_count=int(incident_count or 0),
                ),
            )
            for item, geojson, asset_count, incident_count in rows
            if geojson
        ]
        return FeatureCollection(features=features)

    def pipelines(self, *, zone: str | None = None) -> FeatureCollection:
        try:
            rows = self.repository.list_pipelines(zone=zone)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        features = [
            MapFeature(
                id=segment.external_id,
                geometry=_geometry(geojson),
                properties=PipelineFeatureProperties(
                    external_id=segment.external_id,
                    name=segment.name,
                    status=segment.status,
                    criticality=segment.criticality_score,
                    zone=zone_name,
                    population_served=segment.population_served,
                    active_incident_count=int(incident_count or 0),
                    connected_asset_count=int(asset_count or 0),
                ),
            )
            for segment, zone_name, geojson, incident_count, asset_count in rows
            if geojson
        ]
        return FeatureCollection(features=features)

    def assets(
        self,
        *,
        zone: str | None = None,
        asset_type: AssetType | None = None,
        asset_status: OperationalStatus | None = None,
    ) -> FeatureCollection:
        try:
            rows = self.repository.list_assets(
                zone=zone,
                asset_type=asset_type,
                asset_status=asset_status,
            )
            latest_rows = self.telemetry.latest_for_sensors(
                [asset.id for asset, *_rest in rows if asset.asset_type == AssetType.sensor.value]
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        now = datetime.now(timezone.utc)
        features = [
            self._asset_feature(
                asset,
                zone_name,
                segment_name,
                geojson,
                int(incident_count or 0),
                latest_rows.get(asset.id),
                now,
            )
            for asset, zone_name, segment_name, _segment_id, geojson, incident_count in rows
            if geojson
        ]
        return FeatureCollection(features=features)

    def incidents(
        self,
        *,
        zone: str | None = None,
        incident_severity: SeverityTier | None = None,
        incident_status: IncidentStatus | None = None,
        include_resolved: bool = False,
    ) -> FeatureCollection:
        try:
            rows = self.repository.list_incidents(
                zone=zone,
                incident_severity=incident_severity,
                incident_status=incident_status,
                include_resolved=include_resolved,
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        features = [
            self._incident_feature(incident, sensor_id, segment_id, geojson)
            for incident, sensor_id, segment_id, geojson in rows
            if geojson
        ]
        return FeatureCollection(features=features)

    def summary(
        self,
        *,
        zone: str | None = None,
        asset_type: AssetType | None = None,
        asset_status: OperationalStatus | None = None,
        incident_severity: SeverityTier | None = None,
        incident_status: IncidentStatus | None = None,
        include_resolved: bool = False,
    ) -> MapSummary:
        assets = self.assets(zone=zone, asset_type=asset_type, asset_status=asset_status).features
        incidents = self.incidents(
            zone=zone,
            incident_severity=incident_severity,
            incident_status=incident_status,
            include_resolved=include_resolved,
        ).features
        try:
            last_update = self.repository.summary_timestamp()
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        return MapSummary(
            visible_zones=len(self.zones(zone=zone).features),
            visible_pipelines=len(self.pipelines(zone=zone).features),
            visible_assets=len(assets),
            online=sum(1 for item in assets if _is_status(item, OperationalStatus.online)),
            degraded=sum(1 for item in assets if _is_status(item, OperationalStatus.degraded)),
            offline=sum(1 for item in assets if _is_status(item, OperationalStatus.offline)),
            active_incidents=sum(1 for item in incidents if _is_active_incident(item)),
            critical_incidents=sum(1 for item in incidents if _is_critical(item)),
            last_data_update=last_update or datetime.now(timezone.utc),
            data_mode="seeded_demo",
        )

    def nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: float,
        feature_type: str | None,
    ) -> NearbyResponse:
        try:
            rows = self.repository.nearby(
                latitude=latitude,
                longitude=longitude,
                radius_m=radius_m,
                feature_type=feature_type,
            )
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc

        items: list[NearbyItem] = []
        for kind, row in rows:
            if kind == "asset":
                asset, zone_name, segment_name, _segment_id, geojson, distance = row
                latest = None
                if asset.asset_type == AssetType.sensor.value:
                    latest = self.telemetry.latest_for_sensor(asset.id)
                feature = self._asset_feature(
                    asset,
                    zone_name,
                    segment_name,
                    geojson,
                    0,
                    latest,
                    datetime.now(timezone.utc),
                )
                items.append(
                    NearbyItem(
                        feature_type="asset",
                        id=asset.external_id,
                        name=asset.name,
                        distance_m=round(float(distance), 1),
                        geometry=feature.geometry,
                        properties=feature.properties,
                    )
                )
            elif kind == "pipeline":
                segment, zone_name, geojson, distance = row
                properties = PipelineFeatureProperties(
                    external_id=segment.external_id,
                    name=segment.name,
                    status=segment.status,
                    criticality=segment.criticality_score,
                    zone=zone_name,
                    population_served=segment.population_served,
                    active_incident_count=0,
                    connected_asset_count=0,
                )
                items.append(
                    NearbyItem(
                        feature_type="pipeline",
                        id=segment.external_id,
                        name=segment.name,
                        distance_m=round(float(distance), 1),
                        geometry=_geometry(geojson),
                        properties=properties,
                    )
                )
            else:
                incident, sensor_id, segment_id, geojson, distance = row
                feature = self._incident_feature(incident, sensor_id, segment_id, geojson)
                items.append(
                    NearbyItem(
                        feature_type="incident",
                        id=incident.incident_number,
                        name=incident.title,
                        distance_m=round(float(distance), 1),
                        geometry=feature.geometry,
                        properties=feature.properties,
                    )
                )
        items.sort(key=lambda item: item.distance_m)
        return NearbyResponse(
            origin={"latitude": latitude, "longitude": longitude},
            radius_m=radius_m,
            items=items,
            total=len(items),
        )

    def _asset_feature(
        self,
        asset: Asset,
        zone_name: str,
        segment_name: str | None,
        geojson: str,
        incident_count: int,
        latest: SensorReading | None = None,
        now: datetime | None = None,
    ) -> MapFeature:
        freshness = None
        latest_time = None
        packet_loss = None
        signal = None
        battery = None
        if asset.asset_type == AssetType.sensor.value:
            clock = now or datetime.now(timezone.utc)
            latest_time = latest.time if latest is not None else None
            freshness = classify_freshness(latest_time, clock)
            if latest is not None:
                packet_loss = latest.packet_loss_pct
                signal = latest.signal_strength_dbm
                battery = latest.battery_pct
        return MapFeature(
            id=asset.external_id,
            geometry=_geometry(geojson),
            properties=AssetFeatureProperties(
                external_id=asset.external_id,
                name=asset.name,
                asset_type=AssetType(asset.asset_type),
                operational_status=OperationalStatus(asset.operational_status),
                health_score=asset.health_score,
                zone=zone_name,
                zone_id=public_zone_id(asset.zone.code) if asset.zone is not None else None,
                location_label=asset.location_label,
                has_cellular_identity=bool(asset.device_msisdn),
                device_msisdn_masked=mask_device_msisdn(asset.device_msisdn),
                pipeline_segment=segment_name,
                active_incident_count=incident_count,
                last_seen_at=asset.last_seen_at,
                latest_reading_at=latest_time,
                telemetry_freshness=freshness,
                latest_packet_loss_pct=packet_loss,
                latest_signal_strength_dbm=signal,
                latest_battery_pct=battery,
            ),
        )

    def _incident_feature(
        self,
        incident: Incident,
        sensor_id: str | None,
        segment_id: str | None,
        geojson: str,
    ) -> MapFeature:
        return MapFeature(
            id=incident.incident_number,
            geometry=_geometry(geojson),
            properties=IncidentFeatureProperties(
                incident_number=incident.incident_number,
                title=incident.title,
                severity=_severity(incident.severity_tier),
                classification=Classification(incident.classification),
                status=IncidentStatus(incident.status),
                detected_at=incident.detected_at,
                related_asset_id=sensor_id,
                related_segment_id=segment_id,
                summary=incident.current_summary,
            ),
        )

    def detections(self, *, zone: str | None = None) -> FeatureCollection:
        try:
            rows = self.detections_repository.map_detections(zone=zone)
        except (OperationalError, InterfaceError) as exc:
            raise DatabaseUnavailableError from exc
        features: list[MapFeature] = []
        for row in rows:
            sensor = row.sensor
            if sensor.latitude is None or sensor.longitude is None:
                continue
            features.append(
                MapFeature(
                    id=row.detection_number,
                    geometry=GeoJSONGeometry(type="Point", coordinates=[sensor.longitude, sensor.latitude]),
                    properties=DetectionFeatureProperties(
                        detection_number=row.detection_number,
                        priority=row.priority,
                        status=row.status,
                        anomaly_score=row.anomaly_score,
                        trigger_reason=row.trigger_reason,
                        rule_code=row.rule.code,
                        sensor_id=sensor.external_id,
                        zone=sensor.zone.name if sensor.zone else "",
                        detected_at=row.detected_at,
                        data_mode=row.data_mode,
                    ),
                )
            )
        return FeatureCollection(features=features)
