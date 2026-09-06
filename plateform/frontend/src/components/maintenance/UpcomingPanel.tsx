import { Link } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import { MAINTENANCE_TYPE_LABELS } from "../../lib/maintenance";
import type { UpcomingMaintenanceItem } from "../../types/maintenance";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { MaintenancePriorityBadge, OverdueBadge } from "./MaintenanceBadges";

export function UpcomingPanel({ items }: { items: UpcomingMaintenanceItem[] }) {
  const groups = items.reduce<Record<string, UpcomingMaintenanceItem[]>>((acc, item) => {
    const key = item.due_at.slice(0, 10);
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Upcoming maintenance</h3>
      <p className="mt-0.5 text-sm text-ink-muted">Grouped by due date. Demonstration schedule only.</p>
      {items.length === 0 ? (
        <EmptyState title="No upcoming work" description="Open work orders will appear here by due date." />
      ) : (
        <div className="mt-4 space-y-4">
          {Object.entries(groups).map(([day, rows]) => (
            <div key={day}>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{day}</p>
              <ul className="mt-2 space-y-2">
                {rows.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={`/maintenance/work-orders/${encodeURIComponent(item.id)}`}
                      className="block rounded-2xl border border-line p-3 hover:border-teal/30"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <MaintenancePriorityBadge priority={item.priority} />
                        {item.overdue ? <OverdueBadge /> : null}
                      </div>
                      <p className="mt-2 text-sm font-medium text-ink">{item.title}</p>
                      <p className="mt-0.5 text-xs text-ink-muted">
                        {item.asset_id} · {item.zone} · {MAINTENANCE_TYPE_LABELS[item.maintenance_type]}
                      </p>
                      <p className="mt-1 text-xs text-ink-muted">{formatDateTime(item.due_at)}</p>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
