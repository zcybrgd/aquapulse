from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

from app.api.routes import (
    agent_audit,
    analytics,
    assets,
    compat,
    dashboard,
    detections,
    health,
    incidents,
    integrations,
    maintenance,
    map as map_routes,
    network_health,
    operations,
    telemetry,
)
from app.core.config import get_settings
from app.core.exceptions import (
    AgentAuditEventNotFoundError,
    AgentAuditRunNotFoundError,
    AgentIntegrationError,
    AnalyticsValidationError,
    AssetNotFoundError,
    AssetValidationError,
    DatabaseUnavailableError,
    DetectionConflictError,
    DetectionNotFoundError,
    IncidentConflictError,
    IncidentNotFoundError,
    MaintenanceConflictError,
    MaintenancePlanNotFoundError,
    MaintenanceWorkOrderNotFoundError,
    NetworkEventNotFoundError,
    ResponseTaskNotFoundError,
    TelemetryValidationError,
    ZoneNotFoundError,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AquaPulse operational control platform API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(incidents.router, prefix=settings.api_prefix)
app.include_router(assets.router, prefix=settings.api_prefix)
app.include_router(map_routes.router, prefix=settings.api_prefix)
app.include_router(telemetry.router, prefix=settings.api_prefix)
app.include_router(detections.router, prefix=settings.api_prefix)
app.include_router(operations.router, prefix=settings.api_prefix)
app.include_router(maintenance.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(integrations.router, prefix=settings.api_prefix)
app.include_router(network_health.router, prefix=settings.api_prefix)
app.include_router(agent_audit.router, prefix=settings.api_prefix)
app.include_router(compat.router, prefix=settings.api_prefix)


@app.exception_handler(AgentIntegrationError)
def agent_integration_error_handler(_request: Request, exc: AgentIntegrationError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.http_detail})


@app.exception_handler(IncidentNotFoundError)
def incident_not_found_handler(_request: Request, exc: IncidentNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(AssetNotFoundError)
def asset_not_found_handler(_request: Request, exc: AssetNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(AssetValidationError)
def asset_validation_handler(_request: Request, exc: AssetValidationError) -> JSONResponse:
    status = 404 if exc.code == "asset_zone_not_found" else 422
    return JSONResponse(status_code=status, content={"detail": exc.http_detail})


@app.exception_handler(DetectionNotFoundError)
def detection_not_found_handler(_request: Request, exc: DetectionNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(DetectionConflictError)
def detection_conflict_handler(_request: Request, exc: DetectionConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": exc.http_detail})


@app.exception_handler(IncidentConflictError)
def incident_conflict_handler(_request: Request, exc: IncidentConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": exc.http_detail})


@app.exception_handler(ResponseTaskNotFoundError)
def response_task_not_found_handler(_request: Request, exc: ResponseTaskNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(MaintenanceWorkOrderNotFoundError)
def maintenance_work_order_not_found_handler(
    _request: Request, exc: MaintenanceWorkOrderNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(MaintenancePlanNotFoundError)
def maintenance_plan_not_found_handler(_request: Request, exc: MaintenancePlanNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(MaintenanceConflictError)
def maintenance_conflict_handler(_request: Request, exc: MaintenanceConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": exc.http_detail})


@app.exception_handler(NetworkEventNotFoundError)
def network_event_not_found_handler(_request: Request, exc: NetworkEventNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(AgentAuditRunNotFoundError)
def agent_audit_run_not_found_handler(_request: Request, exc: AgentAuditRunNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(AgentAuditEventNotFoundError)
def agent_audit_event_not_found_handler(_request: Request, exc: AgentAuditEventNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(TelemetryValidationError)
def telemetry_validation_handler(_request: Request, exc: TelemetryValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.http_detail})


@app.exception_handler(AnalyticsValidationError)
def analytics_validation_handler(_request: Request, exc: AnalyticsValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.http_detail})


@app.exception_handler(ZoneNotFoundError)
def zone_not_found_handler(_request: Request, exc: ZoneNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.http_detail})


@app.exception_handler(DatabaseUnavailableError)
def database_unavailable_handler(_request: Request, exc: DatabaseUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": exc.http_detail})


@app.exception_handler(OperationalError)
def operational_error_handler(_request: Request, _exc: OperationalError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": DatabaseUnavailableError.http_detail})


@app.exception_handler(InterfaceError)
def interface_error_handler(_request: Request, _exc: InterfaceError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": DatabaseUnavailableError.http_detail})


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
