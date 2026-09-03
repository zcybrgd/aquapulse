"""
Stage 2: Anomaly Investigation (Network vs. Asset Disambiguation) -- Section 5.B.

Given a cluster flagged `suspicious` by Stage 1, this module runs the CAMARA
diagnostic sequence:

    Device Reachability Status
        REACHABLE          -> confirmed_anomaly           (proceed to risk assessment)
        UNREACHABLE         -> Congestion Insights + temperature check
            HIGH congestion AND ambient_temp_c >= 50C
                            -> likely_connectivity_artifact (silence physical alert)
            LOW/MEDIUM congestion
                            -> confirmed_instrument_fault   (bypass risk matrix)
        api_unavailable     -> insufficient_data + requeue / escalate

Every CAMARA call goes through the try/except wrappers in `camara_client.py`
so a platform outage can never be misread as a legitimate reading.
"""
from __future__ import annotations

from aia.camara_client import CamaraClient, safe_get_congestion_insights, safe_get_device_reachability_status
from aia.config import MAX_INSUFFICIENT_DATA_RETRIES, THERMAL_DEGRADATION_TEMP_C
from aia.models import Classification, ClusterInvestigationState, CongestionLevel, ReachabilityStatus


def investigate(
    state: ClusterInvestigationState,
    camara_client: CamaraClient,
) -> ClusterInvestigationState:
    """
    Runs the Stage 2 disambiguation sequence in-place on `state` and returns it.
    """
    current_ambient_temp = state.window.readings[-1].ambient_temp_c

    reach = safe_get_device_reachability_status(camara_client, state.sensor_cluster_id)
    state.camara_reachability_status = reach.status
    state.api_unavailable = reach.api_unavailable
    state.api_error_detail = reach.error_detail

    if reach.api_unavailable:
        _apply_insufficient_data(state)
        return state

    if reach.status == ReachabilityStatus.REACHABLE:
        # Device is talking; abnormal telemetry with healthy comms means the
        # anomaly is physical. Congestion is still fetched for the output
        # payload's network_status block, but it does not change the
        # classification per Section 5.B.1.
        congestion = safe_get_congestion_insights(camara_client, state.sensor_cluster_id)
        if congestion.api_unavailable:
            # Reachability succeeded but congestion failed -- reachability
            # alone is sufficient to confirm the physical anomaly, so we do
            # not degrade to insufficient_data; we just note the missing
            # congestion reading for the confidence score.
            state.camara_congestion_level = CongestionLevel.UNAVAILABLE
            state.api_unavailable = True  # affects C_CAMARA in the confidence score only
        else:
            state.camara_congestion_level = congestion.level
        state.classification = Classification.CONFIRMED_ANOMALY
        state.consecutive_insufficient_data_cycles = 0
        return state

    # UNREACHABLE -> query Congestion Insights to disambiguate thermal cell
    # degradation from a genuine instrument/hardware fault.
    congestion = safe_get_congestion_insights(camara_client, state.sensor_cluster_id)
    state.camara_congestion_level = congestion.level
    if congestion.api_unavailable:
        state.api_unavailable = True
        _apply_insufficient_data(state)
        return state

    if congestion.level == CongestionLevel.HIGH and current_ambient_temp >= THERMAL_DEGRADATION_TEMP_C:
        state.classification = Classification.LIKELY_CONNECTIVITY_ARTIFACT
    else:
        state.classification = Classification.CONFIRMED_INSTRUMENT_FAULT
        state.is_stale_pre_outage_data = True

    state.consecutive_insufficient_data_cycles = 0
    return state


def _apply_insufficient_data(state: ClusterInvestigationState) -> None:
    """
    Section 5.B.3-4: on API failure, never infer a classification. Requeue
    with elevated priority; after 3 consecutive cycles, escalate to a human
    operator.
    """
    state.classification = Classification.INSUFFICIENT_DATA
    state.consecutive_insufficient_data_cycles += 1
    if state.consecutive_insufficient_data_cycles >= MAX_INSUFFICIENT_DATA_RETRIES:
        state.escalate_to_human = True
        state.requeue = False
    else:
        state.requeue = True
        state.escalate_to_human = False


def check_platform_wide_outage(states: list[ClusterInvestigationState]) -> bool:
    """
    Section 5.B.3: if api_unavailable is detected across multiple clusters in
    the same batch, a high-severity "Nokia NaC Platform Offline" system alert
    should fire. Returns True when that condition is met (>= 2 clusters).
    """
    unavailable_count = sum(1 for s in states if s.api_unavailable)
    return unavailable_count >= 2
