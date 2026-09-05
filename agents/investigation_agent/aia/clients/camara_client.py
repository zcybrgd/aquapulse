"""
CAMARA / Nokia Network-as-Code integration layer.

This module is the single integration boundary between AquaPulse and
Nokia's Network-as-Code SDK.

Responsibilities:
    - Initialize the Nokia Network-as-Code client.
    - Map AquaPulse sensor-cluster identifiers to CAMARA device identifiers.
    - Expose Device Reachability through a high-level CamaraClient facade.
    - Convert external API failures into controlled results for Stage 2.
    - Provide the Stage 2 compatibility wrappers:
        * safe_get_device_reachability_status()
        * safe_get_congestion_insights()

Business logic must remain in the investigation layer.

FastAPI must NOT be implemented in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from network_as_code import NetworkAsCodeApi

from aia.clients.device_reachability import DeviceReachabilityClient
from aia.config import RAPIDAPI_HOST, get_rapidapi_key
from aia.models import CongestionLevel, ReachabilityStatus




class MockCamaraClient:
    """Mock CAMARA client for testing reachability and congestion behavior."""

    def __init__(self, overrides: dict[str, dict[str, Any]] | None = None) -> None:
        self.overrides = overrides or {}

    def get_device_reachability_for_cluster(self, sensor_cluster_id: str) -> Any:
        override = self.overrides.get(sensor_cluster_id, {})
        if override.get("raise"):
            raise RuntimeError(f"Simulated CAMARA API failure for {sensor_cluster_id}")

        reachability = override.get("reachability", ReachabilityStatus.REACHABLE)

        @dataclass
        class MockReachabilityResponse:
            reachable: bool | None

        if reachability == ReachabilityStatus.REACHABLE:
            return MockReachabilityResponse(reachable=True)
        elif reachability == ReachabilityStatus.UNREACHABLE:
            return MockReachabilityResponse(reachable=False)
        return MockReachabilityResponse(reachable=None)

    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult:
        override = self.overrides.get(sensor_cluster_id, {})
        if override.get("raise"):
            raise RuntimeError(f"Simulated CAMARA Congestion API failure for {sensor_cluster_id}")

        congestion = override.get("congestion", CongestionLevel.LOW)
        return CongestionResult(level=congestion, api_unavailable=False)

        
# ============================================================================
# AquaPulse -> CAMARA device mapping
# ============================================================================

DEVICE_ID_MAP: dict[str, str] = {
    # Online / DATA-connected Nokia simulator device.
    "device-14-valve-A": "+99999991001",

    # Nokia simulator device representing lost connectivity.
    "device-offline-demo": "+99999991003",

    # Existing AquaPulse failure scenario.
    "device-14-valve-A-fail": "+99999991001",
}


# ============================================================================
# Controlled CAMARA results
# ============================================================================


class CamaraErrorType(str, Enum):
    """Categories used to describe CAMARA integration failures."""

    API_UNAVAILABLE = "api_unavailable"
    INVALID_DEVICE = "invalid_device"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ReachabilityResult:
    """
    Controlled result returned by the CAMARA reachability wrapper.

    This prevents Stage 2 from having to understand the Nokia SDK's
    exception types or response objects.
    """

    status: ReachabilityStatus
    api_unavailable: bool = False
    error_detail: str | None = None


@dataclass(slots=True)
class CongestionResult:
    """
    Controlled result returned by the congestion wrapper.

    Congestion Insights is not currently implemented by the AquaPulse
    Nokia integration. Therefore the default result is UNAVAILABLE,
    rather than inventing a LOW/MEDIUM/HIGH value.
    """

    level: CongestionLevel
    api_unavailable: bool = False
    error_detail: str | None = None


# ============================================================================
# High-level CAMARA facade
# ============================================================================


class CamaraClient:
    """
    High-level facade for CAMARA APIs exposed through Nokia
    Network-as-Code.

    The rest of AquaPulse should communicate with CAMARA through this class
    rather than importing or using NetworkAsCodeApi directly.

    Architecture:

        AquaPulse
            |
            v
        CamaraClient
            |
            +--> DeviceReachabilityClient
            |
            +--> future CAMARA capabilities
            |
            v
        NetworkAsCodeApi
            |
            v
        Nokia Network-as-Code
    """

    def __init__(self, network_client: NetworkAsCodeApi) -> None:
        """
        Initialize the CAMARA client.

        Args:
            network_client:
                An initialized Nokia Network-as-Code API client.
        """
        self._network_client = network_client

        self.device_reachability = DeviceReachabilityClient(
            network_client
        )

    # ------------------------------------------------------------------------
    # Device mapping
    # ------------------------------------------------------------------------

    def resolve_device_phone_number(self, sensor_cluster_id: str) -> str:
        """
        Resolve an AquaPulse sensor-cluster identifier to the phone number
        expected by the Nokia Network-as-Code Device Reachability API.

        Args:
            sensor_cluster_id:
                AquaPulse's internal device / cluster identifier.

        Returns:
            The CAMARA/Nokia phone number.

        Raises:
            KeyError:
                If the AquaPulse device is not registered.
        """
        try:
            return DEVICE_ID_MAP[sensor_cluster_id]
        except KeyError as exc:
            raise KeyError(
                f"No CAMARA device mapping exists for "
                f"sensor_cluster_id={sensor_cluster_id!r}."
            ) from exc

    # ------------------------------------------------------------------------
    # Device Reachability
    # ------------------------------------------------------------------------

    def get_device_reachability(
        self,
        phone_number: str,
    ) -> Any:
        """
        Retrieve the raw Device Reachability response.

        This method intentionally returns the native Nokia SDK response.
        Higher-level error handling is implemented by the safe wrapper below.

        Args:
            phone_number:
                The device phone number used by Nokia Network-as-Code.

        Returns:
            The raw Device Reachability response.

        Raises:
            Exception:
                Any exception raised by the Nokia SDK.
        """
        return self.device_reachability.get_reachability_status(
            phone_number
        )

    def get_device_reachability_for_cluster(
        self,
        sensor_cluster_id: str,
    ) -> Any:
        """
        Retrieve Device Reachability using an AquaPulse sensor-cluster ID.

        This is the preferred application-level method because AquaPulse
        should not need to know Nokia simulator phone numbers.
        """
        phone_number = self.resolve_device_phone_number(
            sensor_cluster_id
        )

        return self.get_device_reachability(phone_number)

    # ------------------------------------------------------------------------
    # Congestion Insights
    # ------------------------------------------------------------------------

    def get_congestion_insights(
        self,
        sensor_cluster_id: str,
    ) -> CongestionResult:
        """
        Retrieve congestion information for an AquaPulse device.

        Congestion Insights is intentionally not fabricated here.

        The current Nokia integration only implements Device Reachability.
        Until a real Congestion Insights capability is connected, Stage 2
        receives an explicit UNAVAILABLE result.

        Args:
            sensor_cluster_id:
                AquaPulse sensor-cluster identifier.

        Returns:
            CongestionResult with level=UNAVAILABLE.
        """
        # Validate that the AquaPulse device is known even though the
        # capability itself is not implemented yet.
        self.resolve_device_phone_number(sensor_cluster_id)

        return CongestionResult(
            level=CongestionLevel.UNAVAILABLE,
            api_unavailable=True,
            error_detail=(
                "CAMARA Congestion Insights is not implemented in the "
                "current Nokia Network-as-Code integration."
            ),
        )


# ============================================================================
# Safe Stage 2 wrappers
# ============================================================================


def safe_get_device_reachability_status(
    camara_client: CamaraClient,
    sensor_cluster_id: str,
) -> ReachabilityResult:
    """
    Safely retrieve Device Reachability for a sensor cluster.

    Stage 2 must never interpret an API failure as a legitimate
    UNREACHABLE device.

    Therefore:

        successful API call
            -> REACHABLE / UNREACHABLE

        API failure
            -> UNKNOWN + api_unavailable=True

    Args:
        camara_client:
            Configured CamaraClient instance.

        sensor_cluster_id:
            AquaPulse sensor-cluster identifier.

    Returns:
        Controlled ReachabilityResult.
    """
    try:
        response = camara_client.get_device_reachability_for_cluster(
            sensor_cluster_id
        )

    except KeyError as exc:
        return ReachabilityResult(
            status=ReachabilityStatus.UNKNOWN,
            api_unavailable=True,
            error_detail=str(exc),
        )

    except Exception as exc:
        return ReachabilityResult(
            status=ReachabilityStatus.UNKNOWN,
            api_unavailable=True,
            error_detail=(
                f"{type(exc).__name__}: {exc}"
            ),
        )

    reachable = getattr(response, "reachable", None)

    if reachable is True:
        return ReachabilityResult(
            status=ReachabilityStatus.REACHABLE,
        )

    if reachable is False:
        return ReachabilityResult(
            status=ReachabilityStatus.UNREACHABLE,
        )

    # A successful HTTP/API call that does not contain a usable
    # reachability value must not be interpreted as UNREACHABLE.
    return ReachabilityResult(
        status=ReachabilityStatus.UNKNOWN,
        api_unavailable=True,
        error_detail=(
            "CAMARA Device Reachability response did not contain "
            "a valid boolean 'reachable' field."
        ),
    )


def safe_get_congestion_insights(
    camara_client: CamaraClient,
    sensor_cluster_id: str,
) -> CongestionResult:
    """
    Safely retrieve Congestion Insights.

    At present, the underlying capability is not implemented, so the
    result is explicitly marked UNAVAILABLE.

    This function exists as the controlled Stage 2 boundary and can later
    delegate to a real CAMARA Congestion Insights implementation without
    changing investigation.py.
    """
    try:
        return camara_client.get_congestion_insights(
            sensor_cluster_id
        )

    except KeyError as exc:
        return CongestionResult(
            level=CongestionLevel.UNAVAILABLE,
            api_unavailable=True,
            error_detail=str(exc),
        )

    except Exception as exc:
        return CongestionResult(
            level=CongestionLevel.UNAVAILABLE,
            api_unavailable=True,
            error_detail=(
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================================
# Client factory
# ============================================================================


def build_camara_client() -> CamaraClient:
    """
    Build a fully configured CamaraClient using Nokia Network-as-Code.

    Environment configuration is handled centrally by aia.config.

    Returns:
        A configured CamaraClient instance.

    Raises:
        RuntimeError:
            If RAPIDAPI_KEY is not configured.
    """
    network_client = NetworkAsCodeApi(
        rapidapi_host=RAPIDAPI_HOST,
        api_key=get_rapidapi_key(),
    )

    return CamaraClient(network_client)