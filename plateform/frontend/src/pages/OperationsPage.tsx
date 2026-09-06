import { Link } from "react-router-dom";
import { ClipboardList, RefreshCw, TimerReset } from "lucide-react";

import { OperationsCardList, OperationsTable } from "../components/operations/OperationsQueue";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useOperationsFilters } from "../hooks/useOperationsFilters";
import { useOperationsQueue } from "../hooks/useOperationsQueue";
import { formatDateTime } from "../lib/format";
import { SEVERITY_LABELS, STATUS_LABELS, TASK_PRIORITY_LABELS } from "../lib/incidents";
import type { OperationsFilters } from "../types/incidents";

function Kpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string;
  hint: string;
}) {
  return (
    <Card className="min-w-0 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink-muted">{hint}</p>
    </Card>
  );
}

export function OperationsPage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useOperationsFilters();
  const { data, loading, error, updatedAt, reload } = useOperationsQueue(filters);
  const summary = data?.summary;
  const zones = [...new Set((data?.items ?? []).map((item) => item.zone))].sort();
  const assignees = [...new Set((data?.items ?? []).map((item) => item.assigned_to || item.assigned_operator).filter(Boolean))] as string[];

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Operations Center</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Coordinate active incidents. These actions record human workflow only. No physical
            command is executed.{" "}
            <Link to="/incidents" className="font-medium text-teal hover:underline">
              Incident Center
            </Link>{" "}
            remains the catalogue of every incident.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <p className="text-ink-muted">
            Updated {updatedAt ? formatDateTime(updatedAt.toISOString()) : "—"}
          </p>
          <Button variant="secondary" onClick={reload} disabled={loading}>
            <RefreshCw size={14} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      {loading && !data ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </div>
      ) : null}

      {error ? <ErrorState message={error} onRetry={reload} /> : null}

      {summary ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <Kpi label="Active" value={summary.active_incidents} hint="Open operational work" />
          <Kpi label="Unacknowledged" value={summary.unacknowledged} hint="Still waiting in open" />
          <Kpi label="Responding" value={summary.responding} hint="Coordinated response" />
          <Kpi label="Awaiting approval" value={summary.awaiting_approval} hint="Needs a decision" />
          <Kpi label="Overdue tasks" value={summary.overdue_tasks} hint="Past due, still open" />
          <Kpi label="Critical active" value={summary.critical_active} hint="Tier 3 in progress" />
        </div>
      ) : null}

      {data ? (
        <>
          <Card className="min-w-0 p-4">
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
              <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
                Search
                <input
                  value={filters.search}
                  onChange={(event) => setFilters({ search: event.target.value })}
                  className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
                  placeholder="Incident, zone or assignee"
                />
              </label>
              <FilterSelect
                label="Status"
                value={filters.status}
                onChange={(status) => setFilters({ status: status as OperationsFilters["status"] })}
                options={Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))}
              />
              <FilterSelect
                label="Severity"
                value={filters.severity}
                onChange={(severity) => setFilters({ severity: severity as OperationsFilters["severity"] })}
                options={Object.entries(SEVERITY_LABELS).map(([value, label]) => ({ value, label }))}
              />
              <FilterSelect
                label="Zone"
                value={filters.zone}
                onChange={(zone) => setFilters({ zone })}
                options={zones.map((zone) => ({ value: zone, label: zone }))}
              />
              <FilterSelect
                label="Assignment"
                value={filters.assigned_to}
                onChange={(assigned_to) => setFilters({ assigned_to })}
                options={assignees.map((name) => ({ value: name, label: name }))}
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-ink-muted">Showing {data.total} incidents</p>
              {hasActiveFilters ? (
                <Button variant="ghost" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : null}
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(18rem,1fr)]">
            <div className="min-w-0">
              {data.items.length === 0 ? (
                <Card>
                  <EmptyState
                    title="No incidents need attention with these filters"
                    description="Clear the filters or open the Incident Center to review the full catalogue."
                  />
                </Card>
              ) : (
                <>
                  <OperationsTable items={data.items} />
                  <OperationsCardList items={data.items} />
                </>
              )}
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <TaskSideList
                title="Overdue tasks"
                icon={TimerReset}
                items={data.overdue_tasks}
                empty="No overdue response tasks."
              />
              <TaskSideList
                title="Upcoming tasks"
                icon={ClipboardList}
                items={data.upcoming_tasks}
                empty="No upcoming due dates."
              />
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-critical">Safety</p>
                <p className="mt-2 text-sm text-ink-muted">
                  Isolation, valve closure and pressure adjustment remain future capabilities.
                  Operational command integration is not enabled.
                </p>
              </Card>
            </div>
          </div>
        </>
      ) : null}

    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function TaskSideList({
  title,
  icon: Icon,
  items,
  empty,
}: {
  title: string;
  icon: typeof ClipboardList;
  items: OperationsQueueResponseTasks;
  empty: string;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2">
        <Icon size={16} className="text-teal" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
      </div>
      {items.length === 0 ? <p className="mt-3 text-sm text-ink-muted">{empty}</p> : null}
      <ul className="mt-3 space-y-3">
        {items.map((task) => (
          <li key={task.public_id} className="rounded-2xl border border-line p-3">
            <p className="text-xs font-medium text-teal">{task.public_id}</p>
            <p className="mt-1 text-sm font-medium text-ink">{task.title}</p>
            <p className="mt-1 text-xs text-ink-muted">
              {task.incident_id} · {TASK_PRIORITY_LABELS[task.priority]}
              {task.due_at ? ` · due ${formatDateTime(task.due_at)}` : ""}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {task.incident_id ? (
                <Link
                  to={`/incidents/${encodeURIComponent(task.incident_id)}`}
                  className="text-sm font-medium text-teal hover:underline"
                >
                  Open incident
                </Link>
              ) : null}
              {task.overdue ? <span className="text-xs font-medium text-critical">Overdue</span> : null}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

type OperationsQueueResponseTasks = import("../types/incidents").ResponseTaskItem[];
