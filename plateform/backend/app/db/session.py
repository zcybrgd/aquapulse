from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.sql_echo,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _session_factory


def reset_engine() -> None:
    """Dispose the cached engine so tests can bind a different DATABASE_URL."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    except DatabaseUnavailableError:
        db.rollback()
        raise
    finally:
        db.close()


def database_is_reachable() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def postgis_is_available() -> bool:
    """True when the PostGIS extension is installed. Does not return connection details."""
    return _extension_is_available("postgis")


def timescaledb_is_available() -> bool:
    """True when the TimescaleDB extension is installed. Does not return connection details."""
    return _extension_is_available("timescaledb")


def _extension_is_available(name: str) -> bool:
    try:
        with get_engine().connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = :name"),
                {"name": name},
            ).scalar()
        return bool(exists)
    except Exception:
        return False
