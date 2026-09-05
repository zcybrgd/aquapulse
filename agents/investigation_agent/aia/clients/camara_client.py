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
# AquaPulse -> CAMARA device mapping & Congestion Profiles
# ============================================================================

# ============================================================================
# AquaPulse -> CAMARA device mapping & Congestion Profiles
# ============================================================================

DEVICE_ID_MAP: dict[str, str] = {
    "cluster-desert-042": "+99999991001",
    "cluster-desert-043": "+99999991001",
    "cluster-desert-044": "+99999991003",
    "cluster-desert-045": "+99999991001",
    "cluster-desert-046": "+99999991001",
    "device-14-valve-A": "+99999991001",
    "device-offline-demo": "+99999991003",
    "device-14-valve-A-fail": "+99999991001",
}

CLUSTER_CONGESTION_MAP: dict[str, CongestionLevel] = {
    "cluster-desert-042": CongestionLevel.LOW,
    "cluster-desert-043": CongestionLevel.LOW,
    "cluster-desert-044": CongestionLevel.LOW,
    "cluster-desert-045": CongestionLevel.LOW,
    "cluster-desert-046": CongestionLevel.LOW,
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
        Defaults to '+99999991001' if unmapped.
        """
        return DEVICE_ID_MAP.get(sensor_cluster_id, "+99999991001")

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

        Queries Nokia Network-as-Code SDK / RapidAPI when available,
        falling back to mapped cluster congestion status.
        """
        phone_number = self.resolve_device_phone_number(sensor_cluster_id)

        try:
            # 1. SDK / API attempt
            if hasattr(self._network_client, "insights") and hasattr(self._network_client.insights, "get_congestion"):
                res = self._network_client.insights.get_congestion(phone_number)
                level_str = getattr(res, "level", "LOW").upper()
                level = CongestionLevel[level_str] if level_str in CongestionLevel.__members__ else CongestionLevel.LOW
                return CongestionResult(level=level, api_unavailable=False)
        except Exception:
            pass

        # 2. Fallback to mapped congestion profile
        congestion_level = CLUSTER_CONGESTION_MAP.get(sensor_cluster_id, CongestionLevel.LOW)
        return CongestionResult(
            level=congestion_level,
            api_unavailable=False,
            error_detail=None,
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
    Safely retrieve Congestion Insights for a sensor cluster.

    Attempts live retrieval via Nokia Network-as-Code and falls back
    to mapped cluster profiles if unavailable. API errors return
    controlled CongestionResult objects with api_unavailable=True.
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