"""
Top-level batch pipeline (Section 2: the full 4-stage AIA flow).

`AnomalyInvestigationAgent.process_batch()` is the single entry point:

    1. For every telemetry_window in the batch, run Stage 1 detection.
       Healthy windows are archived to the TelemetryStore and skipped.
    2. Suspicious windows are run through the compiled LangGraph
       (Stage 2 investigation -> Stage 3 risk -> Stage 4 narration).
    3. Cross-batch retry state (Section 5.B.4 / Scenario E) is tracked here,
       since it spans multiple `process_batch()` calls.
    4. A validated `AIABatchOutputPayload` is returned, containing only
       investigated (suspicious/anomalous/faulted) clusters -- normal
       telemetry never appears in the output (Section 7).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from aia.camara_client import CamaraClient
from aia.detection import BaselineStore, detect_and_learn
from aia.investigation import check_platform_wide_outage
from aia.models import (
    AIABatchOutputPayload,
    Classification,
    ClusterInvestigationState,
    CriticalityMetrics,
    InvestigatedThreat,
    NetworkStatus,
    PhysicalDeviations,
    StreamingBatch,
    TelemetryWindow,
)
from aia.storage import TelemetryStore
from aia.topology import TopologyCache

logger = logging.getLogger("aia")


@dataclass
class RetryTracker:
    """
    Cross-batch bookkeeping for clusters stuck in `insufficient_data`
    (Section 5.B.4) so consecutive-cycle counts survive between
    `process_batch()` calls.
    """
    consecutive_cycles: dict[str, int] = field(default_factory=dict)

    def get(self, cluster_id: str) -> int:
        return self.consecutive_cycles.get(cluster_id, 0)

    def record_insufficient_data(self, cluster_id: str) -> int:
        self.consecutive_cycles[cluster_id] = self.consecutive_cycles.get(cluster_id, 0) + 1
        return self.consecutive_cycles[cluster_id]

    def reset(self, cluster_id: str) -> None:
        self.consecutive_cycles.pop(cluster_id, None)


class AnomalyInvestigationAgent:
    def __init__(
        self,
        baseline_store: BaselineStore,
        topology: TopologyCache,
        telemetry_store: TelemetryStore,
        camara_client: CamaraClient,
        anthropic_client=None,
        anthropic_model: str = "claude-sonnet-4-6",
        retry_tracker: RetryTracker | None = None,
    ):
        from aia.graph import build_investigation_graph

        self.baseline_store = baseline_store
        self.topology = topology
        self.telemetry_store = telemetry_store
        self.camara_client = camara_client
        self.retry_tracker = retry_tracker or RetryTracker()
        self._graph = build_investigation_graph(
            camara_client=camara_client,
            topology=topology,
            anthropic_client=anthropic_client,
            model=anthropic_model,
        )

    # -- Stage 1 --------------------------------------------------------

    def _run_detection(self, batch: StreamingBatch) -> tuple[list[TelemetryWindow], int]:
        suspicious: list[TelemetryWindow] = []
        for window in batch.telemetry_windows:
            result = detect_and_learn(window, self.baseline_store)
            if result.is_suspicious:
                logger.info("Cluster %s flagged suspicious: %s", window.sensor_cluster_id, result.reason)
                suspicious.append(window)
            else:
                self.telemetry_store.archive_normal_window(window)
        return suspicious, len(batch.telemetry_windows)

    # -- Stages 2-4 (per cluster, via LangGraph) -------------------------

    def _investigate_cluster(self, window: TelemetryWindow) -> ClusterInvestigationState:
        state = ClusterInvestigationState(
            sensor_cluster_id=window.sensor_cluster_id,
            window=window,
            consecutive_insufficient_data_cycles=self.retry_tracker.get(window.sensor_cluster_id),
        )
        final_state_dict = self._graph.invoke(state)
        final_state = (
            final_state_dict
            if isinstance(final_state_dict, ClusterInvestigationState)
            else ClusterInvestigationState.model_validate(final_state_dict)
        )

        if final_state.classification == Classification.INSUFFICIENT_DATA:
            cycles = self.retry_tracker.record_insufficient_data(window.sensor_cluster_id)
            final_state.consecutive_insufficient_data_cycles = cycles
            final_state.escalate_to_human = cycles >= 3
            final_state.requeue = not final_state.escalate_to_human
        else:
            self.retry_tracker.reset(window.sensor_cluster_id)

        return final_state

    # -- Output compilation (Section 7) ----------------------------------

    @staticmethod
    def _to_investigated_threat(state: ClusterInvestigationState) -> InvestigatedThreat:
        return InvestigatedThreat(
            anomaly_id=state.anomaly_id,
            sensor_cluster_id=state.sensor_cluster_id,
            segment_id=state.segment_id or f"unknown-{state.sensor_cluster_id}",
            classification=state.classification,
            severity_tier=state.severity_tier or 1,
            network_status=NetworkStatus(
                camara_reachability_status=(
                    state.camara_reachability_status.value
                    if state.camara_reachability_status
                    else "UNKNOWN"
                ),
                camara_congestion_level=state.camara_congestion_level or "UNAVAILABLE",
                api_unavailable=state.api_unavailable,
            ),
            physical_deviations=PhysicalDeviations(
                pressure_drop_pct=state.pressure_drop_pct,
                flow_surge_pct=state.flow_surge_pct,
                pressure_slope=state.pressure_slope,
                flow_slope=state.flow_slope,
                is_stale_pre_outage_data=state.is_stale_pre_outage_data,
            ),
            criticality_metrics=CriticalityMetrics(
                criticality_score=state.criticality_score or 1,
                proximity_to_reservoir_m=state.proximity_to_reservoir_m or 0.0,
                population_served=state.population_served or 0,
                associated_valve_id=state.associated_valve_id or f"unknown-{state.sensor_cluster_id}",
            ),
            operator_justification=state.operator_justification or "",
            confidence_score=state.confidence_score or 0.0,
        )

    # -- Public entry point ------------------------------------------------

    def process_batch(self, batch: StreamingBatch) -> AIABatchOutputPayload:
        start = time.monotonic()

        suspicious_windows, total_clusters = self._run_detection(batch)

        investigated_states = [self._investigate_cluster(w) for w in suspicious_windows]

        if check_platform_wide_outage(investigated_states):
            logger.critical(
                "Nokia NaC Platform Offline: api_unavailable across %d clusters in batch %s",
                sum(1 for s in investigated_states if s.api_unavailable),
                batch.batch_id,
            )

        for s in investigated_states:
            if s.escalate_to_human:
                logger.critical(
                    "Cluster %s escalated to human operator after %d consecutive "
                    "insufficient_data cycles",
                    s.sensor_cluster_id,
                    s.consecutive_insufficient_data_cycles,
                )

        threats = [self._to_investigated_threat(s) for s in investigated_states]

        elapsed = time.monotonic() - start
        logger.info("Batch %s processed in %.3fs (%d/%d flagged)", batch.batch_id, elapsed, len(threats), total_clusters)

        return AIABatchOutputPayload(
            batch_id=batch.batch_id,
            analysis_timestamp=batch.timestamp,
            total_clusters_analyzed=total_clusters,
            anomalies_detected_count=len(threats),
            investigated_threats=threats,
        )
