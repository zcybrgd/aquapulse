from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from aia.clients.camara_client import CamaraClient
from aia.clients.storage import TelemetryStore
from aia.clients.topology import TopologyCache
from aia.config import MAX_INSUFFICIENT_DATA_RETRIES
from aia.nodes.detection import BaselineStore, detect_and_learn
from aia.nodes.investigation import check_platform_wide_outage
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

logger = logging.getLogger("aia")


@dataclass
class RetryTracker:

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
        leak_detector=None,
        llm_client=None,
        llm_model: str = "anthropic/claude-3.5-sonnet",
        retry_tracker: RetryTracker | None = None,
        # Sequential by default: parallel clusters each fire a Stage 4 Mistral
        # call, and the free/dev Mistral tier's rate limit is low enough that
        # even 2 concurrent narration calls can trigger a 429. Raise this only
        # if your Mistral tier's RPS budget can absorb concurrent narration.
        max_workers: int = 4,
    ):
        from aia.graph.builder import build_investigation_graph

        self.baseline_store = baseline_store
        self.topology = topology
        self.telemetry_store = telemetry_store
        self.camara_client = camara_client
        self.leak_detector = leak_detector
        self.retry_tracker = retry_tracker or RetryTracker()
        self._max_workers = max_workers
        self._graph = build_investigation_graph(
            camara_client=camara_client,
            topology=topology,
            llm_client=llm_client,
            model=llm_model,
        )

    # -- Stage 1 --------------------------------------------------------

    def _run_detection(self, batch: StreamingBatch) -> tuple[list[TelemetryWindow], int]:
        suspicious: list[TelemetryWindow] = []
        for window in batch.telemetry_windows:
            # Look up pipe metadata from topology for the ML model
            segment = self.topology.get_segment_for_cluster(window.sensor_cluster_id)
            pipe_diameter = segment.pipe_diameter_mm if segment else 200.0
            pipe_material = "HDPE"  # default; could be extended in SegmentTopology
            pipe_age = 10           # default; could be extended in SegmentTopology

            result = detect_and_learn(
                window, self.baseline_store,
                leak_detector=self.leak_detector,
                pipe_diameter_mm=pipe_diameter,
                pipe_age_years=pipe_age,
                pipe_material=pipe_material,
            )
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
            final_state.escalate_to_human = cycles >= MAX_INSUFFICIENT_DATA_RETRIES
            final_state.requeue = not final_state.escalate_to_human
        else:
            self.retry_tracker.reset(window.sensor_cluster_id)

        return final_state

    def _investigate_clusters_parallel(
        self, windows: list[TelemetryWindow]
    ) -> list[ClusterInvestigationState]:
        """
        Process multiple suspicious clusters in parallel using a thread pool.
        Each cluster gets its own LangGraph invocation (Stages 2-4).
        """
        if len(windows) <= 1:
            return [self._investigate_cluster(w) for w in windows]

        results: list[ClusterInvestigationState] = []
        with ThreadPoolExecutor(max_workers=min(self._max_workers, len(windows))) as executor:
            future_to_window = {
                executor.submit(self._investigate_cluster, w): w
                for w in windows
            }
            for future in as_completed(future_to_window):
                try:
                    results.append(future.result())
                except Exception:
                    window = future_to_window[future]
                    logger.exception(
                        "Investigation failed for cluster %s", window.sensor_cluster_id
                    )
        return results


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
                estimated_volume_loss_lpm=state.estimated_volume_loss_lpm,
            ),
            criticality_metrics=CriticalityMetrics(
                criticality_score=state.criticality_score or 1,
                proximity_to_reservoir_m=state.proximity_to_reservoir_m or 0.0,
                population_served=state.population_served or 0,
                associated_valve_id=state.associated_valve_id or f"unknown-{state.sensor_cluster_id}",
                pipe_diameter_mm=state.pipe_diameter_mm or 200.0,
            ),
            operator_justification=state.operator_justification or "",
            confidence_score=state.confidence_score or 0.0,
        )

    # -- Public entry point ------------------------------------------------

    def process_batch(self, batch: StreamingBatch) -> AIABatchOutputPayload:
        start = time.monotonic()

        suspicious_windows, total_clusters = self._run_detection(batch)

        # Process suspicious clusters in parallel (multi-instance)
        investigated_states = self._investigate_clusters_parallel(suspicious_windows)

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