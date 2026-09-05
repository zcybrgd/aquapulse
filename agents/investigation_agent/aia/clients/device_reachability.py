from __future__ import annotations

from typing import Any

from network_as_code import NetworkAsCodeApi


class DeviceReachabilityClient:
    """
    Client for the CAMARA Device Reachability API exposed through
    Nokia Network-as-Code.

    This class is responsible only for communicating with the
    Device Reachability capability of the Nokia Network-as-Code SDK.

    Application-specific concerns such as:
        - AquaPulse device IDs
        - HTTP/FastAPI responses
        - device-to-phone-number mappings
        - configuration
        - error translation

    belong to higher layers of the application.
    """

    def __init__(self, network_client: NetworkAsCodeApi) -> None:
        """
        Initialize the Device Reachability client.

        Args:
            network_client:
                An initialized Nokia Network-as-Code API client.
        """
        self._network_client = network_client

    def get_reachability_status(self, phone_number: str) -> Any:
        """
        Retrieve the reachability status of a device.

        The phone number is passed directly to the Nokia
        Network-as-Code Device Reachability API.

        Args:
            phone_number:
                The phone number identifying the target device.

                For Nokia's simulator, examples include:
                    +99999991000
                    +99999991001
                    +99999991002
                    +99999991003

        Returns:
            The raw response returned by the Nokia Network-as-Code SDK.

            The response contains information such as:
                - reachable
                - connectivity
                - lastStatusTime

        Raises:
            ValueError:
                If phone_number is empty.

            Exception:
                Any exception raised by the Nokia Network-as-Code SDK
                is propagated to the caller.
        """
        if not phone_number or not phone_number.strip():
            raise ValueError("phone_number must not be empty.")

        return self._network_client.device_status.retrieve_reachability_status(
            device={
                "phone_number": phone_number,
            }
        )
