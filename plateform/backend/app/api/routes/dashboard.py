from fastapi import APIRouter, Depends, Query

from app.api.deps import get_asset_service, get_incident_service, get_operations_service, get_telemetry_service
from app.schemas.dashboard import DashboardSummary, TelemetryReading, TelemetryResponse
from app.schemas.telemetry import TelemetryRange
from app.services.assets import AssetService
from app.services.incidents import IncidentService
from app.services.operations import OperationsService
from app.services.telemetry import TelemetryService
from app.services.telemetry_constants import DATA_MODE, KPA_TO_BAR, LPS_TO_M3H

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    incidents: IncidentService = Depends(get_incident_service),
    assets: AssetService = Depends(get_asset_service),
    telemetry: TelemetryService = Depends(get_telemetry_service),
    operations: OperationsService = Depends(get_operations_service),
) -> DashboardSummary:
    active, critical, water_loss, awaiting, responding = incidents.dashboard_counts()
    online_sensors, total_sensors = assets.sensor_counts()
    network = telemetry.network_summary()
    network_health = network.average_packet_delivery_pct
    if network_health is None:
        network_health = 0.0
    return DashboardSummary(
        active_incidents=active,
        critical_incidents=critical,
        online_sensors=online_sensors,
        total_sensors=total_sensors,
        network_health_percent=round(min(100.0, max(0.0, network_health)), 1),
        estimated_water_loss_m3=water_loss,
        average_response_time_min=11.4,
        awaiting_approval=awaiting,
        responding=responding,
        overdue_response_tasks=operations.overdue_task_count(),
    )


@router.get("/telemetry", response_model=TelemetryResponse)
def get_dashboard_telemetry(
    range: TelemetryRange = Query(default=TelemetryRange.one_hour),
    service: TelemetryService = Depends(get_telemetry_service),
) -> TelemetryResponse:
    samples = service.dashboard_series(range.value)
    network = service.network_summary()
    readings = [
        TelemetryReading(
            timestamp=sample.time,
            pressure=round((sample.pressure_kpa or 0.0) * KPA_TO_BAR, 3),
            flow_rate=round((sample.flow_lps or 0.0) * LPS_TO_M3H, 2),
            packet_loss=sample.packet_loss_pct if sample.packet_loss_pct is not None else 0.0,
        )
        for sample in samples
        if sample.pressure_kpa is not None or sample.flow_lps is not None
    ]
    return TelemetryResponse(
        readings=readings,
        range=range.value,
        data_mode=DATA_MODE,
        last_updated=network.last_telemetry_at,
        network_health_percent=network.average_packet_delivery_pct,
    )
