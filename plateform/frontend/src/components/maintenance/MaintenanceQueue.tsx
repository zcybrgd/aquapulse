import { Link, useLocation } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import { MAINTENANCE_TYPE_LABELS, primaryWorkOrderAction } from "../../lib/maintenance";
import type { WorkOrderSummary } from "../../types/maintenance";
import { AssetTypeBadge } from "../assets/AssetTypeBadge";
import { Card } from "../ui/Card";
import { MaintenancePriorityBadge, OverdueBadge, WorkOrderStatusBadge } from "./MaintenanceBadges";

function detailsPath(id: string, search: string): string {
  return `/maintenance/work-orders/${encodeURIComponent(id)}${search}`;
}

export function MaintenanceTable({ items }: { items: WorkOrderSummary[] }) {
  const location = useLocation();

  return (
    <Card className="hidden min-w-0 overflow-x-auto xl:block">
      <table className="w-full min-w-[56rem] border-collapse text-left text-sm">
        <thead className="bg-page text-xs font-medium uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="min-w-[11rem] px-4 py-3">Work order</th>
            <th className="whitespace-nowrap px-4 py-3">Due</th>
            <th className="min-w-[8rem] px-4 py-3">Asset</th>
            <th className="px-4 py-3">Zone</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Assignment</th>
            <th className="whitespace-nowrap px-4 py-3">Status</th>
            <th className="sticky right-0 z-10 whitespace-nowrap bg-page px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.public_id}
              className={`border-t border-line ${item.overdue ? "bg-critical/5" : ""}`}
            >
              <td className="px-4 py-3 align-top">
                <Link
                  to={detailsPath(item.public_id, location.search)}
                  className="font-medium text-ink hover:text-teal"
                >
                  {item.public_id}
                </Link>
                <p className="mt-0.5 truncate text-ink-muted" title={item.title}>
                  {item.title}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  <MaintenancePriorityBadge priority={item.priority} />
                  {item.overdue ? <OverdueBadge /> : null}
                </div>
              </td>
              <td className="px-4 py-3 align-top text-ink-muted">{formatDateTime(item.due_at)}</td>
              <td className="px-4 py-3 align-top">
                <p className="truncate text-ink">{item.asset_name}</p>
                <p className="mt-0.5 text-xs text-ink-muted">{item.asset_id}</p>
              </td>
              <td className="px-4 py-3 align-top text-ink-muted">{item.zone}</td>
              <td className="px-4 py-3 align-top text-ink-muted">
                {MAINTENANCE_TYPE_LABELS[item.maintenance_type]}
              </td>
              <td className="px-4 py-3 align-top text-ink-muted">{item.assigned_to ?? "Unassigned"}</td>
              <td className="whitespace-nowrap px-4 py-3 align-top">
                <WorkOrderStatusBadge status={item.status} />
              </td>
              <td
                className={`sticky right-0 z-10 whitespace-nowrap px-4 py-3 align-top ${
                  item.overdue ? "bg-critical/5" : "bg-white"
                }`}
              >
                <Link
                  to={detailsPath(item.public_id, location.search)}
                  className="text-sm font-medium text-teal hover:underline"
                >
                  {primaryWorkOrderAction(item.allowed_actions).label}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export function MaintenanceCardList({ items }: { items: WorkOrderSummary[] }) {
  const location = useLocation();

  return (
    <ul className="space-y-3 xl:hidden">
      {items.map((item) => (
        <li key={item.public_id}>
          <Link
            to={detailsPath(item.public_id, location.search)}
            className={`card block min-w-0 p-4 hover:border-teal/30 ${item.overdue ? "border-critical/30" : ""}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <AssetTypeBadge type={item.asset_type} />
              <WorkOrderStatusBadge status={item.status} />
              <MaintenancePriorityBadge priority={item.priority} />
              {item.overdue ? <OverdueBadge /> : null}
            </div>
            <p className="mt-2 text-sm font-semibold text-ink">{item.title}</p>
            <p className="mt-0.5 text-xs text-ink-muted">{item.public_id}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-muted">
              <div>
                <dt>Asset</dt>
                <dd className="mt-0.5 text-ink">{item.asset_id}</dd>
              </div>
              <div>
                <dt>Due</dt>
                <dd className="mt-0.5 text-ink">{formatDateTime(item.due_at)}</dd>
              </div>
              <div>
                <dt>Zone</dt>
                <dd className="mt-0.5 text-ink">{item.zone}</dd>
              </div>
              <div>
                <dt>Assigned</dt>
                <dd className="mt-0.5 text-ink">{item.assigned_to ?? "Unassigned"}</dd>
              </div>
            </dl>
            <p className="mt-3 text-sm font-medium text-teal">
              {primaryWorkOrderAction(item.allowed_actions).label}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
