from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.assets.connectivity import mask_device_msisdn, public_zone_id
from app.core.config import Settings, get_settings
from app.core.exceptions import AssetNotFoundError, DeviceNetworkProviderError, IncidentNotFoundError, NetworkEventNotFoundError
from app.db.base import utc_now
from app.db.models import AgentAuditEvent, Asset
from app.db.models.device_network import DeviceNetworkSnapshot
from app.integrations.sanitize import sanitize_payload
from app.network.constants import MOCK_DATA_MODE, NETWORK_AGENT_CODE
from app.network.device_network import (
    SOURCE_MODE_LABELS,
    STALE_FLOOR_SECONDS,
    DeviceNetworkProvider,
    LocationResult,
    ReachabilityResult,
    configured_source_mode,
    haversine_m,
)
from app.network.providers import build_device_network_provider
from app.repositories.agent_audit import AgentAuditRepository
from app.repositories.assets import AssetRepository
from app.repositories.device_network import DeviceNetworkRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.telemetry import TelemetryRepository
from app.schemas.network_health import (
    BulkDeviceNetworkRefreshResponse,
    BulkRefreshError,
    DeviceNetworkHistoryItem,
    DeviceNetworkListResponse,
    DeviceNetworkSnapshotDetail,
    DeviceNetworkSnapshotSummary,
    DeviceNetworkSummary,
    IncidentDeviceNetworkContext,
    LastTelemetry,
    NetworkEventDetail,
    NetworkEventListResponse,
    NetworkEventSummary,
)

logger = logging.getLogger(__name__)


def _event_id(event: AgentAuditEvent) -> str:
    payload = event.output_summary or {}
    value = payload.get("event_id")
    return str(value) if value else event.public_id


class NetworkHealthService:
    def __init__(
        self,
        session: Session,
        provider: DeviceNetworkProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.provider = provider or build_device_network_provider(self.settings)
        self.repository = AgentAuditRepository(session)
        self.snapshots = DeviceNetworkRepository(session)
        self.assets = AssetRepository(session)
        self.incidents = IncidentRepository(session)
        self.telemetry = TelemetryRepository(session)

    @property
    def source_mode(self) -> str:
        return getattr(self.provider, "source_mode", configured_source_mode(
            self.settings.nokia_network_api_enabled,
            self.settings.nokia_network_api_mode,
        ))

    @property
    def data_source_label(self) -> str:
        return SOURCE_MODE_LABELS.get(self.source_mode, "Demonstration data")

    def _stale_after(self) -> timedelta:
        return timedelta(seconds=max(self.settings.nokia_network_cache_seconds * 2, STALE_FLOOR_SECONDS))

    def _is_stale(self, retrieved_at: datetime | None, now: datetime | None = None) -> bool:
        if retrieved_at is None:
            return False
        current = now or utc_now()
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=current.tzinfo)
        return current - retrieved_at > self._stale_after()

    def _within_cache(self, snapshot: DeviceNetworkSnapshot | None, now: datetime) -> bool:
        if snapshot is None:
            return False
        retrieved = snapshot.retrieved_at
        if retrieved.tzinfo is None:
            retrieved = retrieved.replace(tzinfo=now.tzinfo)
        return now - retrieved < timedelta(seconds=self.settings.nokia_network_cache_seconds)

    def _to_event_summary(self, event: AgentAuditEvent) -> NetworkEventSummary:
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

    def _query_events(self, **filters) -> list[AgentAuditEvent]:
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

    def list_events(self, *, page: int = 1, page_size: int = 25, **filters) -> NetworkEventListResponse:
        events = list(reversed(self._query_events(**filters)))
        total = len(events)
        start = max(0, (page - 1) * page_size)
        page_rows = events[start : start + page_size]
        return NetworkEventListResponse(
            items=[self._to_event_summary(event) for event in page_rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_event(self, event_id: str) -> NetworkEventDetail:
        event = self.repository.get_event(event_id)
        if event is None or event.pipeline_stage != "network_management":
            raise NetworkEventNotFoundError(event_id)
        summary = self._to_event_summary(event)
        payload = sanitize_payload(event.output_summary or {})
        return NetworkEventDetail(
            **summary.model_dump(),
            payload=payload,
            input_summary=sanitize_payload(event.input_summary or {}),
            output_summary=payload,
            error_code=event.error_code,
            error_message=event.error_message,
        )

    def _location_offset(self, asset: Asset, snapshot: DeviceNetworkSnapshot | None) -> float | None:
        if (
            snapshot is None
            or not snapshot.network_location_available
            or snapshot.network_latitude is None
            or snapshot.network_longitude is None
            or asset.latitude is None
            or asset.longitude is None
        ):
            return None
        return round(
            haversine_m(
                asset.latitude,
                asset.longitude,
                snapshot.network_latitude,
                snapshot.network_longitude,
            ),
            1,
        )

    def _last_telemetry(self, asset: Asset, readings: dict) -> LastTelemetry | None:
        if asset.asset_type != "sensor":
            return None
        row = readings.get(asset.id)
        if row is None:
            return None
        return LastTelemetry(
            observed_at=row.time,
            pressure_kpa=row.pressure_kpa,
            flow_lps=row.flow_lps,
            temperature_c=row.temperature_c,
        )

    def _to_item(
        self,
        asset: Asset,
        snapshot: DeviceNetworkSnapshot | None,
        *,
        readings: dict | None = None,
        now: datetime | None = None,
    ) -> DeviceNetworkSnapshotSummary:
        current = now or utc_now()
        zone = asset.zone
        return DeviceNetworkSnapshotSummary(
            snapshot_id=snapshot.public_id if snapshot else "",
            asset_id=asset.external_id,
            asset_name=asset.name,
            asset_type=asset.asset_type,
            zone_id=public_zone_id(zone.code) if zone is not None else None,
            zone_name=zone.name if zone is not None else None,
            location_label=asset.location_label,
            registered_latitude=asset.latitude,
            registered_longitude=asset.longitude,
            has_cellular_identity=bool(asset.device_msisdn),
            device_msisdn_masked=mask_device_msisdn(asset.device_msisdn),
            reachability_status=snapshot.reachability_status if snapshot else "not_checked",
            reachable_via=snapshot.reachable_via if snapshot else None,
            reachability_checked_at=snapshot.reachability_checked_at if snapshot else None,
            network_location_available=bool(snapshot.network_location_available) if snapshot else False,
            network_latitude=snapshot.network_latitude if snapshot else None,
            network_longitude=snapshot.network_longitude if snapshot else None,
            accuracy_radius_m=snapshot.accuracy_radius_m if snapshot else None,
            location_area_type=snapshot.location_area_type if snapshot else None,
            location_observed_at=snapshot.location_observed_at if snapshot else None,
            location_offset_m=self._location_offset(asset, snapshot),
            retrieved_at=snapshot.retrieved_at if snapshot else None,
            stale=self._is_stale(snapshot.retrieved_at, current) if snapshot else False,
            provider=snapshot.provider if snapshot else None,
            source_mode=snapshot.source_mode if snapshot else None,
            data_source_label=SOURCE_MODE_LABELS.get(
                snapshot.source_mode if snapshot else self.source_mode,
                self.data_source_label,
            ),
            error_code=snapshot.error_code if snapshot else None,
            error_message=snapshot.error_message if snapshot else None,
            last_telemetry=self._last_telemetry(asset, readings or {}),
        )

    def _matches_filters(
        self,
        item: DeviceNetworkSnapshotSummary,
        *,
        zone: str | None,
        asset_type: str | None,
        reachability: str | None,
        location_available: bool | None,
        cellular_available: bool | None,
        source_mode: str | None,
        search: str | None,
    ) -> bool:
        if zone:
            needle = zone.strip().casefold()
            zone_values = [item.zone_name or "", item.zone_id or ""]
            if not any(needle in value.casefold() for value in zone_values):
                return False
        if asset_type and item.asset_type != asset_type:
            return False
        if reachability:
            if reachability == "unknown_or_not_checked":
                if item.reachability_status not in {"unknown", "not_checked"}:
                    return False
            elif item.reachability_status != reachability:
                return False
        if location_available is not None and item.network_location_available != location_available:
            return False
        if cellular_available is not None and item.has_cellular_identity != cellular_available:
            return False
        if source_mode and (item.source_mode or "") != source_mode:
            return False
        if search:
            haystack = " ".join(
                value
                for value in (
                    item.asset_id,
                    item.asset_name,
                    item.location_label,
                    item.zone_name,
                    item.device_msisdn_masked,
                )
                if value
            ).casefold()
            if search.strip().casefold() not in haystack:
                return False
        return True

    def _filtered_devices(
        self,
        *,
        zone: str | None = None,
        asset_type: str | None = None,
        reachability: str | None = None,
        location_available: bool | None = None,
        cellular_available: bool | None = None,
        source_mode: str | None = None,
        search: str | None = None,
    ) -> list[tuple[Asset, DeviceNetworkSnapshot | None, DeviceNetworkSnapshotSummary]]:
        assets = self.snapshots.list_assets()
        latest = self.snapshots.latest_for_assets([asset.id for asset in assets])
        sensor_ids = [asset.id for asset in assets if asset.asset_type == "sensor"]
        readings = self.telemetry.latest_for_sensors(sensor_ids)
        now = utc_now()
        rows = []
        for asset in assets:
            snapshot = latest.get(asset.id)
            item = self._to_item(asset, snapshot, readings=readings, now=now)
            if self._matches_filters(
                item,
                zone=zone,
                asset_type=asset_type,
                reachability=reachability,
                location_available=location_available,
                cellular_available=cellular_available,
                source_mode=source_mode,
                search=search,
            ):
                rows.append((asset, snapshot, item))
        return rows

    def device_summary(self, **filters) -> DeviceNetworkSummary:
        rows = self._filtered_devices(**filters)
        cellular = sum(1 for asset, _snapshot, _item in rows if asset.device_msisdn)
        reachable = sum(1 for _asset, _snapshot, item in rows if item.reachability_status == "reachable")
        unreachable = sum(1 for _asset, _snapshot, item in rows if item.reachability_status == "unreachable")
        unknown = sum(
            1
            for _asset, _snapshot, item in rows
            if item.reachability_status in {"unknown", "not_checked"}
        )
        located = sum(1 for _asset, _snapshot, item in rows if item.network_location_available)
        stale = sum(1 for _asset, _snapshot, item in rows if item.stale)
        zones = sorted({item.zone_name for _asset, _snapshot, item in rows if item.zone_name})
        environment = (
            "Demonstration environment"
            if self.source_mode in {"seeded_demo", "nokia_simulator"}
            else self.data_source_label
        )
        return DeviceNetworkSummary(
            cellular_devices=cellular,
            reachable=reachable,
            unreachable=unreachable,
            unknown_or_not_checked=unknown,
            network_location_available=located,
            stale_checks=stale,
            last_refresh_at=self.snapshots.latest_retrieved_at(),
            source_mode=self.source_mode,
            data_source_label=self.data_source_label,
            environment_label=environment,
            available_zones=zones,
        )

    def list_devices(self, **filters) -> DeviceNetworkListResponse:
        rows = self._filtered_devices(**filters)
        return DeviceNetworkListResponse(
            items=[item for _asset, _snapshot, item in rows],
            total=len(rows),
            source_mode=self.source_mode,
            data_source_label=self.data_source_label,
            last_refresh_at=self.snapshots.latest_retrieved_at(),
        )

    def get_device(self, asset_id: str) -> DeviceNetworkSnapshotDetail:
        asset = self.assets.get_by_external_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id)
        snapshot = self.snapshots.latest_for_asset(asset.id)
        readings = {}
        if asset.asset_type == "sensor":
            latest = self.telemetry.latest_for_sensor(asset.id)
            if latest is not None:
                readings = {asset.id: latest}
        item = self._to_item(asset, snapshot, readings=readings)
        history = [
            DeviceNetworkHistoryItem(
                snapshot_id=row.public_id,
                reachability_status=row.reachability_status,
                reachable_via=row.reachable_via,
                network_location_available=row.network_location_available,
                network_latitude=row.network_latitude,
                network_longitude=row.network_longitude,
                accuracy_radius_m=row.accuracy_radius_m,
                retrieved_at=row.retrieved_at,
                source_mode=row.source_mode,
                error_code=row.error_code,
            )
            for row in self.snapshots.history_for_asset(asset.id)
        ]
        return DeviceNetworkSnapshotDetail(
            **item.model_dump(),
            snapshot_public_id=snapshot.public_id if snapshot else None,
            request_correlation_id=snapshot.request_correlation_id if snapshot else None,
            history=history,
        )

    def device_history(self, asset_id: str) -> list[DeviceNetworkHistoryItem]:
        return self.get_device(asset_id).history

    def _persist(
        self,
        asset: Asset,
        reachability: ReachabilityResult,
        location: LocationResult,
        *,
        retrieved_at: datetime,
        correlation_id: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> DeviceNetworkSnapshot:
        available = location.available and location.latitude is not None and location.longitude is not None
        snapshot = DeviceNetworkSnapshot(
            public_id=self.snapshots.next_public_id(),
            asset_id=asset.id,
            provider=getattr(self.provider, "provider_name", "unknown"),
            source_mode=self.source_mode,
            reachability_status=reachability.status,
            reachable_via=reachability.reachable_via,
            reachability_checked_at=reachability.checked_at or retrieved_at,
            network_location_available=available,
            network_latitude=location.latitude if available else None,
            network_longitude=location.longitude if available else None,
            accuracy_radius_m=location.accuracy_radius_m if available else None,
            location_area_type=location.area_type if available else None,
            location_observed_at=location.observed_at if available else None,
            retrieved_at=retrieved_at,
            request_correlation_id=correlation_id,
            raw_reachability_payload=sanitize_payload(reachability.raw or {}),
            raw_location_payload=sanitize_payload(location.raw or {}),
            error_code=error_code or reachability.error_code or location.error_code,
            error_message=error_message or reachability.error_message or location.error_message,
        )
        self.snapshots.add(snapshot)
        return snapshot

    async def _query_provider(self, device_msisdn: str) -> tuple[ReachabilityResult, LocationResult]:
        logger.info("Refreshing device network for masked identity %s", mask_device_msisdn(device_msisdn))
        reachability = await self.provider.get_reachability(device_msisdn)
        location = await self.provider.retrieve_location(device_msisdn)
        return reachability, location

    async def refresh_device(self, asset_id: str, force: bool = False) -> DeviceNetworkSnapshotDetail:
        asset = self.assets.get_by_external_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id)
        now = utc_now()
        latest = self.snapshots.latest_for_asset(asset.id)
        if not force and self._within_cache(latest, now):
            detail = self.get_device(asset.external_id)
            detail.cached = True
            return detail
        correlation_id = str(uuid4())
        if not asset.device_msisdn:
            self._persist(
                asset,
                ReachabilityResult(status="not_supported", raw={"reason": "no_msisdn"}),
                LocationResult(raw={"reason": "no_msisdn"}),
                retrieved_at=now,
                correlation_id=correlation_id,
                error_code="msisdn_required",
                error_message="This device has no cellular identity, so Nokia APIs cannot be used.",
            )
            self.session.commit()
            return self.get_device(asset.external_id)
        try:
            reachability, location = await self._query_provider(asset.device_msisdn)
            self._persist(asset, reachability, location, retrieved_at=now, correlation_id=correlation_id)
        except DeviceNetworkProviderError as exc:
            self._persist(
                asset,
                ReachabilityResult(status="unknown", raw={}, error_code=exc.code, error_message=exc.message),
                LocationResult(raw={}, error_code=exc.code, error_message=exc.message),
                retrieved_at=now,
                correlation_id=correlation_id,
                error_code=exc.code,
                error_message=exc.message,
            )
        self.session.commit()
        return self.get_device(asset.external_id)

    async def refresh_many(
        self,
        *,
        force: bool = False,
        asset_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> BulkDeviceNetworkRefreshResponse:
        cap = min(limit or self.settings.nokia_network_bulk_limit, self.settings.nokia_network_bulk_limit)
        wanted = {item.strip().upper() for item in asset_ids or [] if item.strip()}
        assets = [
            asset
            for asset in self.snapshots.list_assets()
            if not wanted or asset.external_id.upper() in wanted
        ][:cap]
        now = utc_now()
        latest_map = self.snapshots.latest_for_assets([asset.id for asset in assets])
        items: list[DeviceNetworkSnapshotSummary] = []
        errors: list[BulkRefreshError] = []
        skipped = 0
        succeeded = 0
        failed = 0
        pending: list[Asset] = []
        for asset in assets:
            latest = latest_map.get(asset.id)
            if not force and self._within_cache(latest, now):
                items.append(self._to_item(asset, latest, now=now))
                skipped += 1
                continue
            if not asset.device_msisdn:
                snapshot = self._persist(
                    asset,
                    ReachabilityResult(status="not_supported", raw={"reason": "no_msisdn"}),
                    LocationResult(raw={"reason": "no_msisdn"}),
                    retrieved_at=now,
                    correlation_id=str(uuid4()),
                    error_code="msisdn_required",
                    error_message="This device has no cellular identity, so Nokia APIs cannot be used.",
                )
                items.append(self._to_item(asset, snapshot, now=now))
                succeeded += 1
                continue
            pending.append(asset)

        semaphore = asyncio.Semaphore(self.settings.nokia_network_concurrency)

        async def fetch(asset: Asset) -> tuple[Asset, ReachabilityResult | None, LocationResult | None, DeviceNetworkProviderError | None]:
            async with semaphore:
                try:
                    reachability, location = await self._query_provider(asset.device_msisdn or "")
                    return asset, reachability, location, None
                except DeviceNetworkProviderError as exc:
                    return asset, None, None, exc

        fetched = await asyncio.gather(*[fetch(asset) for asset in pending]) if pending else []
        for asset, reachability, location, error in fetched:
            if error is not None:
                snapshot = self._persist(
                    asset,
                    ReachabilityResult(status="unknown", raw={}, error_code=error.code, error_message=error.message),
                    LocationResult(raw={}, error_code=error.code, error_message=error.message),
                    retrieved_at=now,
                    correlation_id=str(uuid4()),
                    error_code=error.code,
                    error_message=error.message,
                )
                items.append(self._to_item(asset, snapshot, now=now))
                errors.append(
                    BulkRefreshError(asset_id=asset.external_id, error_code=error.code, error_message=error.message)
                )
                failed += 1
                continue
            snapshot = self._persist(asset, reachability, location, retrieved_at=now, correlation_id=str(uuid4()))
            items.append(self._to_item(asset, snapshot, now=now))
            succeeded += 1
        self.session.commit()
        return BulkDeviceNetworkRefreshResponse(
            requested=len(assets),
            succeeded=succeeded,
            failed=failed,
            skipped_cached=skipped,
            items=items,
            errors=errors,
            source_mode=self.source_mode,
            data_source_label=self.data_source_label,
            partial_success=failed > 0 and succeeded + skipped > 0,
        )

    def incident_context(self, incident_id: str) -> IncidentDeviceNetworkContext:
        incident = self.incidents.get_by_number(incident_id)
        if incident is None:
            raise IncidentNotFoundError(incident_id)
        asset = incident.sensor or incident.valve
        if asset is None:
            return IncidentDeviceNetworkContext(incident_id=incident.incident_number, asset_id=None, available=False)
        snapshot = self.snapshots.latest_for_asset(asset.id)
        item = self._to_item(asset, snapshot)
        return IncidentDeviceNetworkContext(
            incident_id=incident.incident_number,
            asset_id=asset.external_id,
            available=True,
            reachability_status=item.reachability_status,
            reachable_via=item.reachable_via,
            reachability_checked_at=item.reachability_checked_at,
            network_location_available=item.network_location_available,
            network_latitude=item.network_latitude,
            network_longitude=item.network_longitude,
            accuracy_radius_m=item.accuracy_radius_m,
            registered_latitude=item.registered_latitude,
            registered_longitude=item.registered_longitude,
            location_offset_m=item.location_offset_m,
            source_mode=item.source_mode,
            data_source_label=item.data_source_label,
            device_msisdn_masked=item.device_msisdn_masked,
        )

    async def refresh_incident_context(self, incident_id: str, force: bool = False) -> IncidentDeviceNetworkContext:
        incident = self.incidents.get_by_number(incident_id)
        if incident is None:
            raise IncidentNotFoundError(incident_id)
        asset = incident.sensor or incident.valve
        if asset is None:
            return IncidentDeviceNetworkContext(incident_id=incident.incident_number, asset_id=None, available=False)
        await self.refresh_device(asset.external_id, force=force)
        return self.incident_context(incident.incident_number)
