import os

SIMULATOR_URL = os.environ.get("SIMULATOR_URL", "http://simulator:8000")
AIA_SERVICE_URL = os.environ.get("AIA_SERVICE_URL", "http://aia-service:8001")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
