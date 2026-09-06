import { Link } from "react-router-dom";

import { useIncidentMaintenance } from "../../hooks/useIncidentMaintenance";
import { formatDateTime } from "../../lib/format";
import { MAINTENANCE_TYPE_LABELS } from "../../lib/maintenance";
import { OverdueBadge, WorkOrderStatusBadge } from "../maintenance/MaintenanceBadges";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Skeleton } from "../ui/Skeleton";

export function IncidentRelatedMaintenance({ incidentId }: { incidentId: string }) {
  const { data, loading, error } = useIncidentMaintenance(incidentId);

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Related maintenance</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Read-only. Completing maintenance does not resolve this incident.
      </p>
      {loading ? (
        <div className="mt-4 space-y-2">
          <Skeleton className="h-16 w-full" />
        </div>
      ) : null}
      {error ? <div className="mt-3"><ErrorState message={error} /></div> : null}
      {data && data.items.length === 0 ? (
        <EmptyState
          title="No linked work orders"
          description="Operators may optionally attach an existing incident when creating a work order."
        />
      ) : null}
      {data && data.items.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {data.items.map((item) => (
            <li key={item.public_id}>
              <Link
                to={`/maintenance/work-orders/${encodeURIComponent(item.public_id)}`}
                className="block rounded-2xl border border-line p-3 hover:border-teal/30"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-ink">{item.public_id}</p>
                  <WorkOrderStatusBadge status={item.status} />
                  {item.overdue ? <OverdueBadge /> : null}
                </div>
                <p className="mt-1 text-sm text-ink">{item.title}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {MAINTENANCE_TYPE_LABELS[item.maintenance_type]} · Due {formatDateTime(item.due_at)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
      <Link to="/maintenance" className="mt-4 inline-block text-sm font-medium text-teal hover:underline">
        Open Maintenance Center
      </Link>
    </Card>
  );
}
