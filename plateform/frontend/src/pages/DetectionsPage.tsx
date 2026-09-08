import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AgentFindingCardList, AgentFindingTable } from "../components/detections/AgentFindingList";
import { DetectionFiltersBar } from "../components/detections/DetectionFiltersBar";
import { DetectionCardList, DetectionTable } from "../components/detections/DetectionList";
import { DetectionQueueHeader, DetectionSummaryCards } from "../components/detections/DetectionQueueHeader";
import { DetectionListSkeleton } from "../components/detections/DetectionSkeletons";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useActorName } from "../hooks/useActorName";
import { useAgentFindings } from "../hooks/useAgentFindings";
import { useDetectionFilters } from "../hooks/useDetectionFilters";
import { useDetections } from "../hooks/useDetections";
import { useDetectionWorkflow } from "../hooks/useDetectionWorkflow";

type QueueTab = "agent" | "screening";

export function DetectionsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<QueueTab>("agent");
  const { filters, setFilters, clearFilters, hasActiveFilters } = useDetectionFilters();
  const { items, total, stats, zones, rules, sensors, loading, error, reload } = useDetections(filters);
  const findings = useAgentFindings();
  const { actorName } = useActorName();
  const workflow = useDetectionWorkflow();

  const agentBusy = findings.loading || (tab === "screening" && loading);
  const agentError = tab === "agent" ? findings.error : error;
  const retry = tab === "agent" ? findings.reload : reload;

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <DetectionQueueHeader
        stats={stats}
        ready={!loading && !error}
        findingCount={findings.items.length}
        ingestReady
      />

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setTab("agent")}
          className={`rounded-full px-3 py-1.5 text-sm font-medium ${
            tab === "agent" ? "bg-teal text-white" : "bg-page text-ink-muted"
          }`}
        >
          Investigation Agent
          {findings.items.length ? ` · ${findings.items.length}` : ""}
        </button>
        <button
          type="button"
          onClick={() => setTab("screening")}
          className={`rounded-full px-3 py-1.5 text-sm font-medium ${
            tab === "screening" ? "bg-teal text-white" : "bg-page text-ink-muted"
          }`}
        >
          Screening rules
        </button>
      </div>

      {agentBusy ? <DetectionListSkeleton /> : null}
      {!agentBusy && agentError ? <ErrorState message={agentError} onRetry={retry} /> : null}
      {workflow.error ? (
        <p className="rounded-2xl bg-critical/10 px-4 py-3 text-sm text-critical" role="alert">
          {workflow.error}
        </p>
      ) : null}
      {workflow.success ? (
        <p className="rounded-2xl bg-success/10 px-4 py-3 text-sm text-success" role="status">
          {workflow.success}
        </p>
      ) : null}

      {tab === "agent" && !findings.loading && !findings.error ? (
        findings.items.length === 0 ? (
          <div className="card">
            <EmptyState
              title="Awaiting Investigation Agent result"
              description="Waiting for integration. Findings appear after the Investigation Agent POSTs a validated batch."
            />
          </div>
        ) : (
          <>
            <AgentFindingTable items={findings.items} />
            <AgentFindingCardList items={findings.items} />
          </>
        )
      ) : null}

      {tab === "screening" && !loading && !error && stats ? (
        <>
          <DetectionSummaryCards stats={stats} />
          <DetectionFiltersBar
            filters={filters}
            zones={zones}
            rules={rules}
            sensors={sensors}
            resultCount={total}
            hasActiveFilters={hasActiveFilters}
            onChange={setFilters}
            onClear={clearFilters}
          />
          {items.length === 0 ? (
            <div className="card">
              <EmptyState
                title="No screening detections"
                description="Deterministic rules add rows here after a detection run. These are not Investigation Agent results."
              />
            </div>
          ) : (
            <>
              <DetectionTable
                items={items}
                busy={workflow.busy}
                onStartReview={async (id) => {
                  const result = await workflow.startReview(id, { actor_name: actorName });
                  if (result) {
                    await reload();
                    navigate(`/detections/${encodeURIComponent(id)}${window.location.search}`);
                  }
                }}
              />
              <DetectionCardList
                items={items}
                busy={workflow.busy}
                onStartReview={async (id) => {
                  const result = await workflow.startReview(id, { actor_name: actorName });
                  if (result) {
                    await reload();
                    navigate(`/detections/${encodeURIComponent(id)}${window.location.search}`);
                  }
                }}
              />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
