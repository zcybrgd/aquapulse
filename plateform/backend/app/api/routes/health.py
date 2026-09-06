from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.session import database_is_reachable, postgis_is_available, timescaledb_is_available
from app.schemas.dashboard import DatabaseHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


def _extension_states(reachable: bool) -> tuple[str, str]:
    if not reachable:
        return "unavailable", "unavailable"
    return (
        "available" if postgis_is_available() else "unavailable",
        "available" if timescaledb_is_available() else "unavailable",
    )


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    reachable = database_is_reachable()
    postgis, timescaledb = _extension_states(reachable)
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database="connected" if reachable else "unavailable",
        postgis=postgis,
        timescaledb=timescaledb,
    )


@router.get("/health/database", response_model=DatabaseHealthResponse)
def get_database_health() -> DatabaseHealthResponse | JSONResponse:
    reachable = database_is_reachable()
    postgis, timescaledb = _extension_states(reachable)
    payload = DatabaseHealthResponse(
        status="ok" if reachable else "unavailable",
        database="connected" if reachable else "unavailable",
        postgis=postgis,
        timescaledb=timescaledb,
        detail=None if reachable else DatabaseUnavailableError.http_detail,
    )
    if reachable:
        return payload
    return JSONResponse(status_code=503, content=payload.model_dump())
