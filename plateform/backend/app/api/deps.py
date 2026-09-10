from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.integrations.agent_status import AgentStatusChecker, get_agent_status_checker as _get_agent_status_checker
from app.network.providers import build_device_network_provider
from app.services.assets import AssetService
from app.services.detections import DetectionService
from app.services.incidents import IncidentService
from app.services.investigation import InvestigationService
from app.services.map import MapService
from app.services.analytics import AnalyticsService
from app.services.operations import OperationsService
from app.services.compat import CompatibilityService
from app.services.integrations import IntegrationService
from app.services.agent_audit import AgentAuditService
from app.services.maintenance import MaintenanceService
from app.services.network_health import NetworkHealthService
from app.services.telemetry import TelemetryService


def get_incident_service(db: Session = Depends(get_db)) -> IncidentService:
    return IncidentService(db)


def get_asset_service(db: Session = Depends(get_db)) -> AssetService:
    return AssetService(db)


def get_map_service(db: Session = Depends(get_db)) -> MapService:
    return MapService(db)


def get_telemetry_service(db: Session = Depends(get_db)) -> TelemetryService:
    return TelemetryService(db)


def get_detection_service(db: Session = Depends(get_db)) -> DetectionService:
    return DetectionService(db)


def get_investigation_service(db: Session = Depends(get_db)) -> InvestigationService:
    return InvestigationService(db)


def get_operations_service(db: Session = Depends(get_db)) -> OperationsService:
    return OperationsService(db)


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


def get_integration_service(db: Session = Depends(get_db)) -> IntegrationService:
    return IntegrationService(db)


def get_compat_service(db: Session = Depends(get_db)) -> CompatibilityService:
    return CompatibilityService(db)


def get_maintenance_service(db: Session = Depends(get_db)) -> MaintenanceService:
    return MaintenanceService(db)


def get_device_network_provider():
    return build_device_network_provider(get_settings())


def get_network_health_service(
    db: Session = Depends(get_db),
    provider=Depends(get_device_network_provider),
) -> NetworkHealthService:
    return NetworkHealthService(db, provider=provider, settings=get_settings())


def get_agent_audit_service(db: Session = Depends(get_db)) -> AgentAuditService:
    return AgentAuditService(db)


def get_agent_status_checker() -> AgentStatusChecker:
    return _get_agent_status_checker()
