from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

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

# Flexible import for shared rate-limited LLM client
try:
    from agents.shared.llm_client import get_groq_llm
except ImportError:
    try:
        from shared.llm_client import get_groq_llm
    except ImportError:
        get_groq_llm = None


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


@dataclass
class ActiveIncidentTracker:
    """
    Tracks active leak incidents per cluster to suppress duplicate alerts and
    prevent downstream LLM rate-limit exhaustion during ongoing leaks,
    while allowing immediate re-alerting if severity escalates (e.g. Tier 2 -> Tier 3).
    """

    active_incidents: dict[str, float] = field(default_factory=dict)
    active_tiers: dict[str, int] = field(default_factory=dict)
    normal_counts: dict[str, int] = field(default_factory=dict)
    cooldown_seconds: float = 300.0  # 5-minute cooldown before re-alerting on same cluster

    def is_suppressed(self, cluster_id: str, new_tier: int = 1) -> bool:
        return self.should_suppress(cluster_id, new_tier)

    def should_suppress(self, cluster_id: str, new_tier: int = 1) -> bool:
        if cluster_id not in self.active_incidents:
            return False

        prev_tier = self.active_tiers.get(cluster_id, 1)

        # Tier escalation bypasses cooldown suppression
        if new_tier > prev_tier:
            logger.info(
                "Cluster %s severity escalated from Tier %d to Tier %d; bypassing suppression.",
                cluster_id,
                prev_tier,
                new_tier,
            )
            return False

        elapsed = time.monotonic() - self.active_incidents[cluster_id]
        return elapsed < self.cooldown_seconds

    def mark_active(self, cluster_id: str, tier: int = 1) -> None:
        self.update_incident(cluster_id, tier)

    def update_incident(self, cluster_id: str, tier: int = 1) -> None:
        self.active_incidents[cluster_id] = time.monotonic()
        current_max = self.active_tiers.get(cluster_id, 1)
        self.active_tiers[cluster_id] = max(tier, current_max)
        self.normal_counts[cluster_id] = 0

    def record_normal(self, cluster_id: str) -> None:
        if cluster_id in self.active_incidents:
            self.normal_counts[cluster_id] = self.normal_counts.get(cluster_id, 0) + 1
            if self.normal_counts[cluster_id] >= 2:
                logger.info(
                    "Cluster %s telemetry returned to normal; clearing active incident state.",
                    cluster_id,
                )
                self.clear(cluster_id)

    def clear(self, cluster_id: str) -> None:
        self.active_incidents.pop(cluster_id, None)
        self.active_tiers.pop(cluster_id, None)
        self.normal_counts.pop(cluster_id, None)


class AnomalyInvestigationAgent:
    def __init__(
        self,
        baseline_store: BaselineStore,
        topology: TopologyCache,
        telemetry_store: TelemetryStore,
        camara_client: CamaraClient,
        leak_detector=None,
        llm_client=None,
        llm_model: str = "openai/gpt-oss-20b",
        retry_tracker: Optional[RetryTracker] = None,
        incident_tracker: Optional[ActiveIncidentTracker] = None,
        cooldown_seconds: float = 300.0,
        max_workers: int = 4,
    ):
        from aia.graph.builder import build_investigation_graph

        self.baseline_store = baseline_store
        self.topology = topology
        self.telemetry_store = telemetry_store
        self.camara_client = camara_client
        self.leak_detector = leak_detector
        self.retry_tracker = retry_tracker or RetryTracker()
        self.incident_tracker = incident_tracker or ActiveIncidentTracker(
            cooldown_seconds=cooldown_seconds
        )
        self._max_workers = max_workers

        # Default to central rate-limited LLM client if none explicitly injected
        if llm_client is None and get_groq_llm is not None:
            try:
                llm_client = get_groq_llm()
            except Exception as exc:
                logger.warning("Could not automatically initialize shared rate-limited LLM: %s", exc)

        self._graph = build_investigation_graph(
            camara_client=camara_client,
            topology=topology,
            llm_client=llm_client,
            model=llm_model,
        )

    # -- Helper for fast pre-check estimation -----------------------------

    def _estimate_quick_tier(self, window: TelemetryWindow) -> int:
        """Fast rule-based estimation of severity tier prior to LLM/LangGraph invocation."""
        readings = window.readings
        if not readings or len(readings) < 2:
            return 1
        p_start, p_end = readings[0].pressure_psi, readings[-1].pressure_psi
        if p_start <= 0:
            return 1
        drop_pct = ((p_start - p_end) / p_start) * 100.0
        if drop_pct >= 25.0:
            return 3
        elif drop_pct >= 10.0:
            return 2
        return 1

    # -- Stage 1 --------------------------------------------------------

    def _run_detection(self, batch: StreamingBatch) -> tuple[list[TelemetryWindow], int]:
        suspicious: list[TelemetryWindow] = []
        for window in batch.telemetry_windows:
            cluster_id = window.sensor_cluster_id
            segment = self.topology.get_segment_for_cluster(cluster_id)
            pipe_diameter = segment.pipe_diameter_mm if segment else 200.0
            pipe_material = "HDPE"
            pipe_age = 10

            result = detect_and_learn(
                window,
                self.baseline_store,
                leak_detector=self.leak_detector,
                pipe_diameter_mm=pipe_diameter,
                pipe_age_years=pipe_age,
                pipe_material=pipe_material,
            )
            if result.is_suspicious:
                # Pre-investigation suppression check:
                # Avoid invoking expensive LLM calls if active incident is under cooldown
                # AND estimated physical severity tier has not escalated.
                est_tier = self._estimate_quick_tier(window)
                if self.incident_tracker.should_suppress(cluster_id, est_tier):
                    logger.info(
                        "Cluster %s threat (Tier %d) suppressed pre-investigation (active incident under cooldown).",
                        cluster_id,
                        est_tier,
                    )
                    self.telemetry_store.archive_normal_window(window)
                else:
                    logger.info("Cluster %s flagged suspicious: %s", cluster_id, result.reason)
                    suspicious.append(window)
            else:
                self.incident_tracker.record_normal(cluster_id)
                self.telemetry_store.archive_normal_window(window)
        return suspicious, len(batch.telemetry_windows)

    # -- Stages 2-4 (per cluster, via LangGraph) -------------------------

    def _investigate_cluster(self, window: TelemetryWindow) -> ClusterInvestigationState:
        state = ClusterInvestigationState(
            sensor_cluster_id=window.sensor_cluster_id,
            window=window,
            consecutive_insufficient_data_cycles=self.retry_tracker.get(window.sensor_cluster_id),
        )
        try:
            final_state_dict = self._graph.invoke(state)
            final_state = (
                final_state_dict
                if isinstance(final_state_dict, ClusterInvestigationState)
                else ClusterInvestigationState.model_validate(final_state_dict)
            )
        except Exception as exc:
            logger.error(
                "LangGraph execution error for cluster %s (likely 429 rate limit): %s. Applying heuristic fallback.",
                window.sensor_cluster_id,
                exc,
            )
            # Safe heuristic fallback state during API rate limits
            final_state = state
            final_state.classification = Classification.CONFIRMED_ANOMALY
            final_state.operator_justification = (
                f"Heuristic fallback applied due to upstream API rate limit or execution error: {exc}"
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
            return [self._investigate_cluster(w) for w in windows] if windows else []

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

        # Process suspicious clusters in parallel
        investigated_states = self._investigate_clusters_parallel(suspicious_windows)

        if check_platform_wide_outage(investigated_states):
            logger.critical(
                "Nokia NaC Platform Offline: api_unavailable across %d clusters in batch %s",
                sum(1 for s in investigated_states if s.api_unavailable),
                batch.batch_id,
            )

        active_threats: list[InvestigatedThreat] = []
        for s in investigated_states:
            if s.escalate_to_human:
                logger.critical(
                    "Cluster %s escalated to human operator after %d consecutive "
                    "insufficient_data cycles",
                    s.sensor_cluster_id,
                    s.consecutive_insufficient_data_cycles,
                )

            cluster_id = s.sensor_cluster_id
            tier = s.severity_tier or 1

            # Post-investigation check
            if self.incident_tracker.should_suppress(cluster_id, tier):
                logger.info(
                    "Cluster %s threat (Tier %d) suppressed post-investigation (active incident under cooldown).",
                    cluster_id,
                    tier,
                )
                self.telemetry_store.archive_normal_window(s.window)
            else:
                self.incident_tracker.update_incident(cluster_id, tier)
                active_threats.append(self._to_investigated_threat(s))

        elapsed = time.monotonic() - start
        logger.info(
            "Batch %s processed in %.3fs (%d/%d flagged, %d dispatched)",
            batch.batch_id,
            elapsed,
            len(investigated_states),
            total_clusters,
            len(active_threats),
        )

        return AIABatchOutputPayload(
            batch_id=batch.batch_id,
            analysis_timestamp=batch.timestamp,
            total_clusters_analyzed=total_clusters,
            anomalies_detected_count=len(active_threats),
            investigated_threats=active_threats,
        )