import { Link, useLocation } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import { operationsPrimaryAction } from "../../lib/incidents";
import type { OperationsQueueItem } from "../../types/incidents";
import { SeverityBadge } from "../incidents/SeverityBadge";
import { StatusBadge } from "../incidents/StatusBadge";
import { Button } from "../ui/Button";

function incidentPath(id: string, search: string): string {
  return `/incidents/${encodeURIComponent(id)}${search}`;
}

function ActionCell({ item, search }: { item: OperationsQueueItem; search: string }) {
  const action = operationsPrimaryAction(item.allowed_actions, item.status);
  return (
    <Link
      to={incidentPath(item.id, search)}
      className="relative z-10 text-sm font-medium text-teal hover:underline"
      onClick={(event) => event.stopPropagation()}
    >
      {action.label}
    </Link>
  );
}

export function OperationsTable({ items }: { items: OperationsQueueItem[] }) {
  const location = useLocation();

  return (
    <div className="card hidden overflow-hidden xl:block">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-page text-xs font-medium uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="px-4 py-3">Incident</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Assigned</th>
            <th className="px-4 py-3">Progress</th>
            <th className="px-4 py-3">Latest update</th>
            <th className="px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t border-line">
              <td className="px-4 py-3">
                <Link to={incidentPath(item.id, location.search)} className="font-medium text-ink hover:text-teal">
                  {item.incident_number}
                </Link>
                <p className="mt-1 max-w-sm truncate text-ink-muted">{item.title}</p>
                <div className="mt-1">
                  <SeverityBadge severity={item.severity} />
                </div>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={item.status} />
              </td>
              <td className="px-4 py-3 text-ink-muted">{item.assigned_to ?? item.assigned_operator ?? "Unassigned"}</td>
              <td className="px-4 py-3 text-ink-muted">
                {item.open_task_count} open
                {item.overdue_task_count ? ` · ${item.overdue_task_count} overdue` : ""}
              </td>
              <td className="px-4 py-3 text-ink-muted">
                {item.latest_update_at ? formatDateTime(item.latest_update_at) : "—"}
              </td>
              <td className="px-4 py-3">
                <ActionCell item={item} search={location.search} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OperationsCardList({ items }: { items: OperationsQueueItem[] }) {
  const location = useLocation();

  return (
    <ul className="space-y-3 xl:hidden">
      {items.map((item) => {
        const action = operationsPrimaryAction(item.allowed_actions, item.status);
        return (
          <li key={item.id} className="card p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-teal">{item.incident_number}</p>
              <SeverityBadge severity={item.severity} />
              <StatusBadge status={item.status} />
            </div>
            <p className="mt-2 text-sm font-medium text-ink">{item.title}</p>
            <p className="mt-1 text-sm text-ink-muted">
              {item.zone} · {item.assigned_to ?? item.assigned_operator ?? "Unassigned"}
            </p>
            <p className="mt-1 text-xs text-ink-muted">
              {item.open_task_count} open tasks
              {item.overdue_task_count ? ` · ${item.overdue_task_count} overdue` : ""}
            </p>
            <div className="mt-3">
              <Link to={incidentPath(item.id, location.search)}>
                <Button variant="secondary" className="w-full">
                  {action.label}
                </Button>
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
