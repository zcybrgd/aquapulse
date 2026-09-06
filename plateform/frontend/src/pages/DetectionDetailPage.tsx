import { Link, useLocation, useParams } from "react-router-dom";

import { DetectionDetailView } from "../components/detections/DetectionDetailView";
import { DetectionDetailSkeleton } from "../components/detections/DetectionSkeletons";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useActorName } from "../hooks/useActorName";
import { useDetectionDetail } from "../hooks/useDetectionDetail";
import { useDetectionWorkflow } from "../hooks/useDetectionWorkflow";

export function DetectionDetailPage() {
  const { detectionId } = useParams();
  const location = useLocation();
  const { detection, agentInput, history, events, loading, notFound, error, reload, refreshInvestigation } =
    useDetectionDetail(detectionId);
  const { actorName } = useActorName();
  const workflow = useDetectionWorkflow();

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      {loading ? <DetectionDetailSkeleton /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && notFound ? (
        <div className="card p-6">
          <Link to={`/detections${location.search}`} className="text-sm font-medium text-teal hover:underline">
            Back to Investigation Queue
          </Link>
          <EmptyState
            title="Detection not found"
            description="This detection ID is not in the investigation queue. Return to the queue and choose another record."
          />
        </div>
      ) : null}
      {!loading && detection ? (
        <DetectionDetailView
          detection={detection}
          agentInput={agentInput}
          history={history}
          events={events}
          busy={workflow.busy}
          workflowError={workflow.error}
          workflowSuccess={workflow.success}
          onStartReview={async (note) => {
            const result = await workflow.startReview(detection.id, { actor_name: actorName, note });
            if (result) {
              await refreshInvestigation();
            }
            return result;
          }}
          onAddNote={async (note) => {
            const result = await workflow.addNote(detection.id, { actor_name: actorName, note });
            if (result) {
              await refreshInvestigation();
            }
            return result;
          }}
          onDismiss={async (reason, note) => {
            const result = await workflow.dismiss(detection.id, {
              actor_name: actorName,
              reason_code: reason,
              note,
            });
            if (result) {
              await refreshInvestigation();
            }
            return result;
          }}
          onReopen={async (note) => {
            const result = await workflow.reopen(detection.id, { actor_name: actorName, note });
            if (result) {
              await refreshInvestigation();
            }
            return result;
          }}
          onMerge={async (targetId, note) => {
            const result = await workflow.merge(detection.id, {
              actor_name: actorName,
              target_detection_id: targetId,
              note,
            });
            if (result) {
              await refreshInvestigation();
            }
            return result;
          }}
          onPromote={async (payload) => {
            const result = await workflow.promote(detection.id, { actor_name: actorName, ...payload });
            if (result) {
              await refreshInvestigation();
            }
            return result;
          }}
        />
      ) : null}
    </div>
  );
}
