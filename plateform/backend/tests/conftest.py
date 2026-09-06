"""Isolated PostgreSQL tests. These never use the development `aquapulse` database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env", override=False)

DEFAULT_TEST_URL = (
    "postgresql+psycopg://aquapulse:aquapulse@127.0.0.1:"
    f"{os.environ.get('POSTGRES_PORT', '5432')}/aquapulse_test"
)
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)
os.environ["APP_ENV"] = "test"


def _ensure_test_database(url: str) -> None:
    parsed = make_url(url)
    database_name = parsed.database
    if not database_name or database_name == "aquapulse" or not database_name.endswith("_test"):
        raise RuntimeError(
            f"Refusing to run tests against {database_name!r}. "
            "Set TEST_DATABASE_URL to a database whose name ends with _test."
        )
    admin_engine = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def test_database() -> str:
    url = os.environ["DATABASE_URL"]
    try:
        _ensure_test_database(url)
    except Exception as exc:
        pytest.exit(
            "PostgreSQL test database is unavailable. Start it with "
            "`docker compose up -d` from the repository root, then rerun pytest. "
            f"({exc.__class__.__name__})",
            returncode=1,
        )

    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()
    assert get_settings().database_url == url
    assert "aquapulse_test" in get_settings().database_url or get_settings().database_url.rstrip("/").endswith("_test")

    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    from app.scripts.seed_database import seed_database

    seed_database()
    return url


@pytest.fixture()
def client(test_database: str):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
