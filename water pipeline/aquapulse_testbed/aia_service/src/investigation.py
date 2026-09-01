import os
import requests

class CAMARADiagnosticClient:
    def __init__(self, simulator_url=None):
        # Default to the docker-compose service name, fallback to localhost for tests
        self.simulator_url = simulator_url or os.getenv("SIMULATOR_URL", "http://localhost:8001")

    def query_reachability(self, sensor_cluster_id: str) -> dict:
        """
        Query Device Reachability Status CAMARA API.
        """
        url = f"{self.simulator_url}/camara/device-reachability-status/v1"
        try:
            resp = requests.get(url, params={"device_id": sensor_cluster_id}, timeout=3.0)
            if resp.status_code == 200:
                return {
                    "reachability_status": resp.json().get("reachability_status", "REACHABLE"),
                    "api_unavailable": False
                }
            else:
                return {
                    "reachability_status": "UNREACHABLE",
                    "api_unavailable": True
                }
        except Exception:
            return {
                "reachability_status": "UNREACHABLE",
                "api_unavailable": True
            }

    def query_congestion(self, sensor_cluster_id: str) -> dict:
        """
        Query Congestion Insights CAMARA API.
        """
        url = f"{self.simulator_url}/camara/congestion-insights/v1"
        try:
            resp = requests.get(url, params={"device_id": sensor_cluster_id}, timeout=3.0)
            if resp.status_code == 200:
                return {
                    "congestion_level": resp.json().get("congestion_level", "LOW"),
                    "api_unavailable": False
                }
            else:
                return {
                    "congestion_level": "UNAVAILABLE",
                    "api_unavailable": True
                }
        except Exception:
            return {
                "congestion_level": "UNAVAILABLE",
                "api_unavailable": True
            }
