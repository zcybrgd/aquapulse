from __future__ import annotations
from typing import Any

class DeviceReachabilityClient:
    def __init__(self, network_client: Any) -> None:
        self._network_client = network_client

    def get_device_connectivity(self, phone_number: str) -> dict:
        """Returns the raw reachability payload: {connectivity: [...], reachable: bool, lastStatusTime: ...}"""
        status = self._network_client.device_status.retrieve_reachability_status( device={"phone_number": phone_number})
        return status