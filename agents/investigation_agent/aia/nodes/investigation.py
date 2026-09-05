"""
Stage 2: Anomaly Investigation (Network vs. Asset Disambiguation)
-----------------------------------------------------------------

Section 5.B.

Given a cluster flagged `suspicious` by Stage 1, this module runs the
CAMARA diagnostic sequence:

    Device Reachability Status

        REACHABLE
            -> confirmed_anomaly
            -> proceed to risk assessment

        UNREACHABLE
            -> Congestion Insights + temperature check

                HIGH congestion AND ambient_temp_c >= 50C
                    -> likely_connectivity_artifact
                    -> silence physical alert

                LOW/MEDIUM congestion
                    -> confirmed_instrument_fault
                    -> bypass risk matrix

        api_unavailable
            -> insufficient_data
            -> requeue / escalate

Every CAMARA call goes through the controlled wrappers in
`aia.clients.camara_client`.

A platform/API failure is therefore never interpreted as a legitimate
device reading.
"""

from __future__ import annotations

from aia.clients.camara_client import (
    CamaraClient,
    safe_get_congestion_insights,
    safe_get_device_reachability_status,
)
from aia.config import THERMAL_DEGRADATION_TEMP_C
from aia.models import (
    Classification,
    ClusterInvestigationState,
    CongestionLevel,
    ReachabilityStatus,
)


def investigate(
    state: ClusterInvestigationState,
    camara_client: CamaraClient,
) -> ClusterInvestigationState:
    """
    Run the Stage 2 network-vs-asset disambiguation sequence.

    The function mutates and returns the supplied investigation state.

    Decision tree:

        Reachable
            -> confirmed_anomaly

        Unreachable + high congestion + high temperature
            -> likely_connectivity_artifact

        Unreachable + low/medium congestion
            -> confirmed_instrument_fault

        CAMARA unavailable
            -> insufficient_data

    Args:
        state:
            Current per-cluster investigation state.

        camara_client:
            Configured CAMARA integration facade.

    Returns:
        The updated investigation state.
    """

    current_ambient_temp = state.window.readings[-1].ambient_temp_c

    # ----------------------------------------------------------------------
    # 1. Device Reachability
    # ----------------------------------------------------------------------

    reach = safe_get_device_reachability_status(
        camara_client,
        state.sensor_cluster_id,
    )

    state.camara_reachability_status = reach.status
    state.api_error_detail = reach.error_detail

    # ----------------------------------------------------------------------
    # 2. Reachability API unavailable
    # ----------------------------------------------------------------------

    if reach.api_unavailable:
        state.api_unavailable = True
        state.reachability_api_unavailable = True

        _apply_insufficient_data(state)

        return state

    # ----------------------------------------------------------------------
    # 3. Device is reachable
    # ----------------------------------------------------------------------

    if reach.status == ReachabilityStatus.REACHABLE:
        """
        The device is communicating with the network.

        Abnormal telemetry combined with healthy communication indicates
        that the anomaly is physical rather than a connectivity artifact.

        We still attempt to retrieve congestion so that the final output
        can contain network-status information.

        Congestion failure does NOT invalidate the reachability result.
        """

        congestion = safe_get_congestion_insights(
            camara_client,
            state.sensor_cluster_id,
        )

        if congestion.api_unavailable:
            state.camara_congestion_level = (
                CongestionLevel.UNAVAILABLE
            )
            state.congestion_api_unavailable = True

            # Preserve the congestion failure detail if no previous
            # CAMARA error detail exists.
            if state.api_error_detail is None:
                state.api_error_detail = congestion.error_detail

        else:
            state.camara_congestion_level = congestion.level

        state.classification = Classification.CONFIRMED_ANOMALY

        return state

    # ----------------------------------------------------------------------
    # 4. Defensive handling of an unexpected reachability state
    # ----------------------------------------------------------------------

    if reach.status != ReachabilityStatus.UNREACHABLE:
        state.api_unavailable = True
        state.reachability_api_unavailable = True

        if state.api_error_detail is None:
            state.api_error_detail = (
                "Unexpected CAMARA reachability status: "
                f"{reach.status!r}"
            )

        _apply_insufficient_data(state)

        return state

    # ----------------------------------------------------------------------
    # 5. Device is unreachable
    # ----------------------------------------------------------------------

    """
    An unreachable device requires a second diagnostic signal.

    We query Congestion Insights to distinguish a connectivity artifact
    caused by network/thermal degradation from a genuine instrument fault.
    """

    congestion = safe_get_congestion_insights(
        camara_client,
        state.sensor_cluster_id,
    )

    state.camara_congestion_level = congestion.level

    # ----------------------------------------------------------------------
    # 6. Congestion API unavailable
    # ----------------------------------------------------------------------

    if congestion.api_unavailable:
        state.api_unavailable = True
        state.congestion_api_unavailable = True

        if state.api_error_detail is None:
            state.api_error_detail = congestion.error_detail

        _apply_insufficient_data(state)

        return state

    # ----------------------------------------------------------------------
    # 7. High congestion + thermal degradation
    # ----------------------------------------------------------------------

    if (
        congestion.level == CongestionLevel.HIGH
        and current_ambient_temp >= THERMAL_DEGRADATION_TEMP_C
    ):
        state.classification = (
            Classification.LIKELY_CONNECTIVITY_ARTIFACT
        )

        return state

    # ----------------------------------------------------------------------
    # 8. Low / medium congestion -> instrument fault
    # ----------------------------------------------------------------------

    state.classification = Classification.CONFIRMED_INSTRUMENT_FAULT

    # The telemetry preceding the connectivity loss is considered stale
    # with respect to the outage period.
    state.is_stale_pre_outage_data = True

    return state


def _apply_insufficient_data(
    state: ClusterInvestigationState,
) -> None:
    """
    Apply the Stage 2 insufficient-data classification.

    On CAMARA/API failure, never infer a physical classification.
    Mark the state for requeue so the pipeline can track retry cycles.
    """

    state.classification = Classification.INSUFFICIENT_DATA
    state.requeue = True


def check_platform_wide_outage(
    states: list[ClusterInvestigationState],
) -> bool:
    """
    Detect a potential platform-wide Nokia Network-as-Code outage.

    Section 5.B.3:

        If CAMARA API unavailability is observed across at least two
        clusters in the same batch, the caller can raise the system-level
        "Nokia NaC Platform Offline" alert.

    Args:
        states:
            Investigation states from the current batch.

    Returns:
        True when at least two clusters experienced API unavailability.
    """

    unavailable_count = sum(
        1
        for state in states
        if state.api_unavailable
    )

    return unavailable_count >= 2