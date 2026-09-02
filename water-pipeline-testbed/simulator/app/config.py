import os

AIA_SERVICE_URL = os.environ.get("AIA_SERVICE_URL", "http://aia-service:8001")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
TICK_SECONDS = float(os.environ.get("TICK_SECONDS", "2.0"))
BATCH_INTERVAL_TICKS = int(os.environ.get("BATCH_INTERVAL_TICKS", "2"))
