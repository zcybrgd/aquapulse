import { Link } from "react-router-dom";

import { useAssetMaintenance } from "../../hooks/useAssetMaintenance";
import { READ_ONLY_HINT, MAINTENANCE_LABELS } from "../../lib/assets";
import { formatDateTime, formatDisplayDay } from "../../lib/format";
import { MAINTENANCE_TYPE_LABELS } from "../../lib/maintenance";
import type { AssetDetail } from "../../types/assets";
import { OverdueBadge, WorkOrderStatusBadge } from "../maintenance/MaintenanceBadges";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Skeleton } from "../ui/Skeleton";

interface AssetMaintenancePanelProps {
  asset: AssetDetail;
}

export function AssetMaintenancePanel({ asset }: AssetMaintenancePanelProps) {
  const { data, loading, error, reload } = useAssetMaintenance(asset.id);
  const calibration = asset.sensor?.calibration_date ?? null;

  return (
    <Card className="min-w-0 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold text-ink">Maintenance</h3>
        {data?.overdue ? <OverdueBadge /> : null}
      </div>
      <p className="mt-1 text-sm text-ink-muted">{READ_ONLY_HINT}</p>

      {loading ? (
        <div className="mt-4 space-y-2">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-3/4" />
        </div>
      ) : null}
      {error ? <div className="mt-3"><ErrorState message={error} onRetry={reload} /></div> : null}

      {data ? (
        <>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-ink-muted">Last maintenance</dt>
              <dd className="font-medium text-ink">
                {data.last_maintenance_at ? formatDisplayDay(data.last_maintenance_at) : "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-ink-muted">Next planned</dt>
              <dd className="font-medium text-ink">
                {data.next_maintenance_at ? formatDisplayDay(data.next_maintenance_at) : "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-ink-muted">Schedule state</dt>
              <dd className="font-medium text-ink">
                {MAINTENANCE_LABELS[asset.maintenance_state] ?? asset.maintenance_state}
              </dd>
            </div>
            {calibration ? (
              <div className="flex justify-between gap-3">
                <dt className="text-ink-muted">Calibration date</dt>
                <dd className="font-medium text-ink">{formatDisplayDay(calibration)}</dd>
              </div>
            ) : null}
          </dl>

          <h4 className="mt-5 text-sm font-semibold text-ink">Active plans</h4>
          {data.active_plans.length === 0 ? (
            <div className="mt-2">
              <EmptyState
                title="No maintenance plan"
                description="This asset has no enabled plan. Open the Maintenance Center to create work manually."
              />
            </div>
          ) : (
            <ul className="mt-2 space-y-2">
              {data.active_plans.map((plan) => (
                <li key={plan.public_id} className="rounded-2xl border border-line p-3 text-sm">
                  <p className="font-medium text-ink">{plan.name}</p>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {plan.public_id} · {MAINTENANCE_TYPE_LABELS[plan.maintenance_type]} · every{" "}
                    {plan.interval_days} days
                  </p>
                  <p className="mt-1 text-xs text-ink-muted">Next due {formatDateTime(plan.next_due_at)}</p>
                </li>
              ))}
            </ul>
          )}

          <h4 className="mt-5 text-sm font-semibold text-ink">Open work orders</h4>
          {data.open_work_orders.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">No open work orders.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {data.open_work_orders.map((item) => (
                <li key={item.public_id}>
                  <Link
                    to={`/maintenance/work-orders/${encodeURIComponent(item.public_id)}`}
                    className="block rounded-2xl border border-line p-3 hover:border-teal/30"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-ink">{item.public_id}</p>
                      <WorkOrderStatusBadge status={item.status} />
                    </div>
                    <p className="mt-1 text-sm text-ink-muted">{item.title}</p>
                    <p className="mt-1 text-xs text-ink-muted">Due {formatDateTime(item.due_at)}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}

          <h4 className="mt-5 text-sm font-semibold text-ink">Recent completed work</h4>
          {data.recent_completed.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">No completed work recorded yet.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {data.recent_completed.map((item) => (
                <li key={item.public_id}>
                  <Link
                    to={`/maintenance/work-orders/${encodeURIComponent(item.public_id)}`}
                    className="block rounded-2xl border border-line p-3 hover:border-teal/30"
                  >
                    <p className="text-sm font-medium text-ink">{item.public_id}</p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {item.completed_at ? formatDateTime(item.completed_at) : "Completed"}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}

          <Link
            to={`/maintenance?asset_id=${encodeURIComponent(asset.id)}`}
            className="mt-5 inline-block text-sm font-medium text-teal hover:underline"
          >
            Open in Maintenance Center
          </Link>
        </>
      ) : null}
    </Card>
  );
}
