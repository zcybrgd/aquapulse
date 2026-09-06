import { useNavigate } from "react-router-dom";

import { DetectionFiltersBar } from "../components/detections/DetectionFiltersBar";
import { DetectionCardList, DetectionTable } from "../components/detections/DetectionList";
import { DetectionQueueHeader, DetectionSummaryCards } from "../components/detections/DetectionQueueHeader";
import { DetectionListSkeleton } from "../components/detections/DetectionSkeletons";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useActorName } from "../hooks/useActorName";
import { useDetectionFilters } from "../hooks/useDetectionFilters";
import { useDetections } from "../hooks/useDetections";
import { useDetectionWorkflow } from "../hooks/useDetectionWorkflow";

export function DetectionsPage() {
  const navigate = useNavigate();
  const { filters, setFilters, clearFilters, hasActiveFilters } = useDetectionFilters();
  const { items, total, stats, zones, rules, sensors, loading, error, reload } = useDetections(filters);
  const { actorName } = useActorName();
  const workflow = useDetectionWorkflow();

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <DetectionQueueHeader stats={stats} ready={!loading && !error} />

      {loading ? <DetectionListSkeleton /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
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

      {!loading && !error && stats ? (
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
                title="No detections awaiting investigation"
                description="The queue is quiet. Deterministic rules will add rows here after a detection run. Detections are not confirmed incidents."
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
