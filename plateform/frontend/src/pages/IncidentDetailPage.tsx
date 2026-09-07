import { Link, useLocation, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

import { IncidentActions } from "../components/incidents/IncidentActions";
import { IncidentDetailHeader } from "../components/incidents/IncidentDetailHeader";
import { IncidentDetailSkeleton } from "../components/incidents/IncidentDetailSkeleton";
import { IncidentEvidenceList } from "../components/incidents/IncidentEvidenceList";
import { IncidentLocationPanel } from "../components/incidents/IncidentLocationPanel";
import { IncidentDeviceNetworkContext } from "../components/incidents/IncidentDeviceNetworkContext";
import { IncidentNetworkPanel } from "../components/incidents/IncidentNetworkPanel";
import { IncidentOperationsPanel } from "../components/incidents/IncidentOperationsPanel";
import { IncidentRelatedMaintenance } from "../components/incidents/IncidentRelatedMaintenance";
import { IncidentSummaryPanel } from "../components/incidents/IncidentSummaryPanel";
import { IncidentTelemetryChart } from "../components/incidents/IncidentTelemetryChart";
import { IncidentTimeline } from "../components/incidents/IncidentTimeline";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useIncidentDetail } from "../hooks/useIncidentDetail";
import { useIncidentOperations } from "../hooks/useIncidentOperations";

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const location = useLocation();
  const { incident, events, loading, notFound, error, reload } = useIncidentDetail(incidentId);
  const operations = useIncidentOperations(incidentId);
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      {loading ? <IncidentDetailSkeleton /> : null}

      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}

      {!loading && notFound ? (
        <div className="card p-6">
          <Link
            to={`/incidents${location.search}`}
            className="text-sm font-medium text-teal hover:underline"
          >
            Back to Incident Center
          </Link>
          <EmptyState
            title="Incident not found"
            description="This incident ID is not in the current mock set. Return to the Incident Center and choose another record."
          />
        </div>
      ) : null}

      {!loading && incident ? (
        <motion.div
          className="flex flex-col gap-6"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: "easeOut" }}
        >
          <IncidentDetailHeader incident={incident} />
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,1fr)]">
            <div className="flex min-w-0 flex-col gap-4">
              <IncidentSummaryPanel incident={incident} />
              <IncidentTelemetryChart incident={incident} />
              <IncidentTimeline events={events} />
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <IncidentLocationPanel incident={incident} />
              <IncidentNetworkPanel incident={incident} />
              <IncidentDeviceNetworkContext incidentId={incident.id} />
              <IncidentEvidenceList evidence={incident.evidence} />
              <IncidentRelatedMaintenance incidentId={incident.id} />
              {operations.operations ? (
                <IncidentOperationsPanel
                  incidentId={incident.id}
                  operations={operations.operations}
                  onChanged={async () => {
                    await Promise.all([reload(), operations.reload()]);
                  }}
                />
              ) : null}
              <IncidentActions />
            </div>
          </div>
        </motion.div>
      ) : null}
    </div>
  );
}
