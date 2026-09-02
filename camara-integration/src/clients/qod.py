from __future__ import annotations
from typing import Any

class QodClient:
    def __init__(self, network_client: Any) -> None:
        self._network_client = network_client
    def reserve_session(self, phone_number: str, application_server_ip: str, duration_seconds: int):
        return self._network_client.qod.create_session_v1(device={"phone_number": phone_number},application_server={"ipv_4_address": application_server_ip},qos_profile="QOS_L",duration=duration_seconds,)