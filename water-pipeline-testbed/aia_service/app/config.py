import os

SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://simulator:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
POSTGRES_DSN = os.environ.get(
    "POSTGRES_DSN",
    "postgresql://aia:aia@timescaledb:5432/aia",
)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
