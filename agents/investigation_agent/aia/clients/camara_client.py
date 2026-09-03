from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Protocol

from dotenv import load_dotenv
from network_as_code import NetworkAsCodeApi

from device_reachability import DeviceReachabilityClient


from aia.config import (
    CONGESTION_HIGH,
    CONGESTION_LOW,
    CONGESTION_MEDIUM,
)
from aia.models import (
    CongestionLevel,
    ReachabilityStatus,
)


# =============================================================================
# Configuration
# =============================================================================

load_dotenv()

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]

NOKIA_RAPIDAPI_HOST = os.getenv(
    "NOKIA_RAPIDAPI_HOST",
    "network-as-code.nokia.rapidapi.com",
)


# =============================================================================
# Exceptions
# =============================================================================


class CamaraApiError(Exception):
    """
    Raised internally by CAMARA client implementations.

    Exceptions are caught by the safe_* wrappers and converted into
    structured results for the application.
    """


# =============================================================================
# Result Models
# =============================================================================


@dataclass
class ReachabilityResult:
    """
    Result returned by the CAMARA Device Reachability Status API.
    """

    status: ReachabilityStatus | None
    api_unavailable: bool
    error_detail: str | None = None


@dataclass
class CongestionResult:
    """
    Result returned by the CAMARA Congestion Insights API.
    """

    level: CongestionLevel | None
    api_unavailable: bool
    error_detail: str | None = None


# =============================================================================
# CAMARA Client Interface
# =============================================================================


class CamaraClient(Protocol):
    """
    Application-level interface for CAMARA functionality.

    The rest of the application depends on this interface rather than on
    Nokia-specific SDK classes.

    Implementations can therefore be:

        - MockCamaraClient for testing
        - NokiaCamaraClient for the real CAMARA/Nokia integration
    """

    def get_device_reachability_status(
        self,
        sensor_cluster_id: str,
    ) -> ReachabilityResult:
        ...

    def get_congestion_insights(
        self,
        sensor_cluster_id: str,
    ) -> CongestionResult:
        ...


# =============================================================================
# Safe CAMARA Operations
# =============================================================================


def safe_get_device_reachability_status(
    client: CamaraClient,
    sensor_cluster_id: str,
) -> ReachabilityResult:
    """
    Safely retrieve Device Reachability Status.

    Any CAMARA/Nokia error is converted into a structured result instead
    of propagating the exception to the application.
    """

    try:
        return client.get_device_reachability_status(
            sensor_cluster_id
        )

    except Exception as exc:
        return ReachabilityResult(
            status=None,
            api_unavailable=True,
            error_detail=str(exc),
        )


def safe_get_congestion_insights(
    client: CamaraClient,
    sensor_cluster_id: str,
) -> CongestionResult:
    """
    Safely retrieve Congestion Insights.

    Any CAMARA/Nokia error is converted into a structured result instead
    of propagating the exception to the application.
    """

    try:
        return client.get_congestion_insights(
            sensor_cluster_id
        )

    except Exception as exc:
        return CongestionResult(
            level=None,
            api_unavailable=True,
            error_detail=str(exc),
        )


# =============================================================================
# Nokia Device Mapping
# =============================================================================

"""
Application-level sensor/device IDs mapped to the Nokia Network as Code
test-device identifiers.

The mapping is kept inside the CAMARA integration layer so that the rest
of the application does not need to know about Nokia-specific identifiers.
"""

DEVICE_ID_MAP: dict[str, str] = {
    "device-14-valve-A": "+99999991001",
    "device-offline-demo": "+99999991003",

    # This device intentionally uses the same Nokia test device as the
    # reachable device. Any downstream failure is simulated by the
    # application/testbed rather than by CAMARA.
    "device-14-valve-A-fail": "+99999991001",
}


def get_phone_number(sensor_cluster_id: str) -> str:
    """
    Resolve an application-level sensor/device ID to its Nokia test-device
    identifier.
    """

    phone_number = DEVICE_ID_MAP.get(sensor_cluster_id)

    if phone_number is None:
        raise CamaraApiError(
            f"No Nokia test-device mapping for '{sensor_cluster_id}'"
        )

    return phone_number


# =============================================================================
# Mock CAMARA Client
# =============================================================================


@dataclass
class MockCamaraClient:
    """
    Deterministic mock CAMARA client.

    Used for:

        - unit tests
        - integration tests
        - anomaly-investigation scenarios
        - CAMARA outage simulation
        - local development without Nokia API access

    Example:

        MockCamaraClient(
            overrides={
                "cluster-desert-042": {
                    "reachability": ReachabilityStatus.REACHABLE,
                    "congestion": CongestionLevel.LOW,
                }
            }
        )

    To simulate a CAMARA API outage:

        MockCamaraClient(
            overrides={
                "cluster-desert-042": {
                    "raise": True,
                }
            }
        )
    """

    overrides: dict[str, dict] = field(default_factory=dict)
    seed: int = 7

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def get_device_reachability_status(
        self,
        sensor_cluster_id: str,
    ) -> ReachabilityResult:

        cfg = self.overrides.get(sensor_cluster_id, {})

        if cfg.get("raise"):
            raise CamaraApiError(
                f"Simulated Nokia NaC outage for {sensor_cluster_id}"
            )

        status = cfg.get("reachability")

        if status is None:
            status = self._rng.choice(
                [
                    ReachabilityStatus.REACHABLE,
                    ReachabilityStatus.UNREACHABLE,
                ]
            )

        return ReachabilityResult(
            status=status,
            api_unavailable=False,
        )

    def get_congestion_insights(
        self,
        sensor_cluster_id: str,
    ) -> CongestionResult:

        cfg = self.overrides.get(sensor_cluster_id, {})

        if cfg.get("raise"):
            raise CamaraApiError(
                f"Simulated Nokia NaC outage for {sensor_cluster_id}"
            )

        level = cfg.get("congestion")

        if level is None:
            level = self._rng.choice(
                [
                    CongestionLevel.LOW,
                    CongestionLevel.MEDIUM,
                    CongestionLevel.HIGH,
                ]
            )

        return CongestionResult(
            level=level,
            api_unavailable=False,
        )


# =============================================================================
# Real Nokia CAMARA Client
# =============================================================================


class NokiaCamaraClient:
    """
    Real CAMARA client backed by Nokia Network as Code.

    Architecture:

        Application
             |
             v
        CamaraClient
             |
             v
        NokiaCamaraClient
             |
             v
        NetworkAsCodeApi
             |
             v
        DeviceReachabilityClient
             |
             v
        Nokia Network as Code
    """

    def __init__(
        self,
        network_client: NetworkAsCodeApi,
        device_reachability_client: DeviceReachabilityClient,
    ) -> None:

        self._network_client = network_client
        self._device_reachability_client = device_reachability_client

    def get_device_reachability_status(
        self,
        sensor_cluster_id: str,
    ) -> ReachabilityResult:

        phone_number = get_phone_number(sensor_cluster_id)

        try:
            status = (
                self._device_reachability_client
                .get_device_connectivity(phone_number)
            )

        except Exception as exc:
            raise CamaraApiError(
                f"Nokia NaC reachability call failed: {exc}"
            ) from exc

        reachable = bool(
            getattr(status, "reachable", False)
        )

        return ReachabilityResult(
            status=(
                ReachabilityStatus.REACHABLE
                if reachable
                else ReachabilityStatus.UNREACHABLE
            ),
            api_unavailable=False,
        )

    def get_congestion_insights(
        self,
        sensor_cluster_id: str,
    ) -> CongestionResult:

        """
        Retrieve Congestion Insights.

        The first script's Nokia integration does not provide a concrete
        Nokia SDK client for Congestion Insights. Therefore, the method
        preserves the second script's interface without inventing a
        Nokia implementation that has not been established.

        Replace this implementation with the actual Nokia/CAMARA
        Congestion Insights client once its SDK/API integration is
        confirmed.
        """

        # Keep the application-level behavior explicit rather than
        # returning a fabricated congestion level.
        raise CamaraApiError(
            "Nokia CAMARA Congestion Insights integration is not "
            "configured yet."
        )


# =============================================================================
# Nokia CAMARA Client Factory
# =============================================================================


def create_nokia_camara_client() -> NokiaCamaraClient:
    """
    Create the real Nokia Network as Code CAMARA client.

    This follows the same initialization pattern as the first script.
    """

    network_client = NetworkAsCodeApi(
        rapidapi_host=NOKIA_RAPIDAPI_HOST,
        api_key=RAPIDAPI_KEY,
    )

    device_reachability_client = DeviceReachabilityClient(
        network_client
    )

    return NokiaCamaraClient(
        network_client=network_client,
        device_reachability_client=device_reachability_client,
    )


# =============================================================================
# Default CAMARA Client
# =============================================================================

camara_client: CamaraClient = create_nokia_camara_client()
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from aia.config import CONGESTION_HIGH, CONGESTION_LOW, CONGESTION_MEDIUM
from aia.models import CongestionLevel, ReachabilityStatus


class CamaraApiError(Exception):
    """Raised internally by client implementations; always caught at the call site."""


@dataclass
class ReachabilityResult:
    status: Optional[ReachabilityStatus]
    api_unavailable: bool
    error_detail: Optional[str] = None


@dataclass
class CongestionResult:
    level: Optional[CongestionLevel]
    api_unavailable: bool
    error_detail: Optional[str] = None


class CamaraClient(Protocol):
    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult: ...
    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult: ...


def safe_get_device_reachability_status(
    client: CamaraClient, sensor_cluster_id: str
) -> ReachabilityResult:
    """try/except wrapper around Device Reachability Status."""
    try:
        return client.get_device_reachability_status(sensor_cluster_id)
    except Exception as exc: 
        return ReachabilityResult(status=None, api_unavailable=True, error_detail=str(exc))


def safe_get_congestion_insights(
    client: CamaraClient, sensor_cluster_id: str
) -> CongestionResult:
    """try/except wrapper around Congestion Insights."""
    try:
        return client.get_congestion_insights(sensor_cluster_id)
    except Exception as exc: 
        return CongestionResult(level=None, api_unavailable=True, error_detail=str(exc))

@dataclass
class MockCamaraClient:
    """
    Deterministic mock CAMARA client.

    `overrides` lets tests pin exact responses per cluster id, e.g.:

        MockCamaraClient(overrides={
            "cluster-desert-042": {
                "reachability": ReachabilityStatus.REACHABLE,
                "congestion": CongestionLevel.LOW,
            }
        })

    Setting `"raise": True` for a cluster simulates an API outage
    (Scenario D), which the safe_* wrappers above convert to
    api_unavailable=True.
    """
    overrides: dict[str, dict] = field(default_factory=dict)
    seed: int = 7

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult:
        cfg = self.overrides.get(sensor_cluster_id, {})
        if cfg.get("raise"):
            raise CamaraApiError(f"Simulated Nokia NaC outage for {sensor_cluster_id}")
        status = cfg.get("reachability")
        if status is None:
            status = self._rng.choice([ReachabilityStatus.REACHABLE, ReachabilityStatus.UNREACHABLE])
        return ReachabilityResult(status=status, api_unavailable=False)

    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult:
        cfg = self.overrides.get(sensor_cluster_id, {})
        if cfg.get("raise"):
            raise CamaraApiError(f"Simulated Nokia NaC outage for {sensor_cluster_id}")
        level = cfg.get("congestion")
        if level is None:
            level = self._rng.choice([CongestionLevel.LOW, CongestionLevel.MEDIUM, CongestionLevel.HIGH])
        return CongestionResult(level=level, api_unavailable=False)



class HttpCamaraClient:
    """
    Thin HTTP wrapper around the Nokia NaC CAMARA Device Reachability Status
    and Congestion Insights APIs. Endpoint paths follow the CAMARA API Hub
    naming convention; confirm exact paths/schemas against the live sandbox
    per Section 9 Phase 1 before relying on this in production, since path
    and payload details vary by NaC deployment/tenant.
    """

    def __init__(
        self,
        base_url: str,
        token_provider: Callable[[], str],
        timeout_seconds: float = 3.0,
    ):
        import httpx  # imported lazily so httpx is an optional dependency

        self._httpx = httpx
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._timeout = timeout_seconds

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token_provider()}"}

    def get_device_reachability_status(self, sensor_cluster_id: str) -> ReachabilityResult:
        resp = self._httpx.post(
            f"{self._base_url}/device-reachability-status/v0/retrieve",
            json={"device": {"networkAccessIdentifier": sensor_cluster_id}},
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        raw_status = str(payload.get("reachabilityStatus", "")).upper()
        status = ReachabilityStatus.REACHABLE if raw_status == "REACHABLE" else ReachabilityStatus.UNREACHABLE
        return ReachabilityResult(status=status, api_unavailable=False)

    def get_congestion_insights(self, sensor_cluster_id: str) -> CongestionResult:
        resp = self._httpx.post(
            f"{self._base_url}/congestion-insights/v0/insights",
            json={"device": {"networkAccessIdentifier": sensor_cluster_id}},
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        raw_level = str(payload.get("congestionLevel", "")).upper()
        level_map = {
            CONGESTION_HIGH: CongestionLevel.HIGH,
            CONGESTION_MEDIUM: CongestionLevel.MEDIUM,
            CONGESTION_LOW: CongestionLevel.LOW,
        }
        level = level_map.get(raw_level, CongestionLevel.UNAVAILABLE)
        return CongestionResult(level=level, api_unavailable=False)