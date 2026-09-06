import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, RefreshCw } from "lucide-react";

import { MaintenanceFiltersBar } from "../components/maintenance/MaintenanceFiltersBar";
import { MaintenanceCardList, MaintenanceTable } from "../components/maintenance/MaintenanceQueue";
import { UpcomingPanel } from "../components/maintenance/UpcomingPanel";
import { CreateWorkOrderDialog } from "../components/maintenance/WorkOrderDialogs";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useMaintenanceFilters } from "../hooks/useMaintenanceFilters";
import { useMaintenanceQueue } from "../hooks/useMaintenanceQueue";
import { useMaintenanceWorkflow } from "../hooks/useMaintenanceWorkflow";
import { formatDateTime } from "../lib/format";
import type { WorkOrderDetail } from "../types/maintenance";

function Kpi({ label, value, hint }: { label: string; value: number | string; hint: string }) {
  return (
    <Card className="min-w-0 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink-muted">{hint}</p>
    </Card>
  );
}

export function MaintenancePage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useMaintenanceFilters();
  const { data, upcoming, zones, loading, error, updatedAt, reload } = useMaintenanceQueue(filters);
  const workflow = useMaintenanceWorkflow();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const summary = data?.summary;

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Maintenance Center</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Schedule and record human maintenance work. These records do not execute device
            commands.{" "}
            <Link to="/assets" className="font-medium text-teal hover:underline">
              Asset Registry
            </Link>{" "}
            remains the catalogue of every device.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <p className="text-ink-muted">Updated {updatedAt ? formatDateTime(updatedAt.toISOString()) : "—"}</p>
          <Button variant="secondary" onClick={reload} disabled={loading}>
            <RefreshCw size={14} aria-hidden="true" />
            Refresh
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={14} aria-hidden="true" />
            New work order
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
          <Kpi label="Overdue" value={summary.overdue} hint="Past due, still open" />
          <Kpi label="Due in 7 days" value={summary.due_within_7_days} hint="Open and approaching" />
          <Kpi label="In progress" value={summary.in_progress} hint="Work has started" />
          <Kpi label="Completed" value={summary.completed_in_period} hint="Selected demonstration period" />
          <Kpi label="Critical" value={summary.critical} hint="Open critical priority" />
          <Kpi label="No plan" value={summary.assets_without_plan} hint="Assets without an enabled plan" />
        </div>
      ) : null}

      {data ? (
        <>
          <MaintenanceFiltersBar
            filters={filters}
            zones={zones}
            resultCount={data.total}
            hasActiveFilters={hasActiveFilters}
            onChange={setFilters}
            onClear={clearFilters}
          />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(18rem,1fr)]">
            <div className="min-w-0">
              {data.items.length === 0 ? (
                <Card>
                  <EmptyState
                    title="No work orders match these filters"
                    description="Clear the filters or create a new administrative work order."
                  />
                </Card>
              ) : (
                <>
                  <MaintenanceTable items={data.items} />
                  <MaintenanceCardList items={data.items} />
                </>
              )}
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <UpcomingPanel items={upcoming} />
              <Card className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-critical">Safety</p>
                <p className="mt-2 text-sm text-ink-muted">
                  Maintenance records describe human work. Completing or cancelling a record does
                  not change asset operational status, valve position or incident status, and does
                  not execute a physical device command.
                </p>
              </Card>
            </div>
          </div>
        </>
      ) : null}

      {createOpen ? (
        <CreateWorkOrderDialog
          busy={workflow.busy}
          error={workflow.error}
          defaultAssetId={filters.asset_id || undefined}
          onClose={() => {
            workflow.clearError();
            setCreateOpen(false);
          }}
          onSubmit={async (payload) => {
            const created = (await workflow.create(payload)) as WorkOrderDetail | null;
            if (created) {
              reload();
              navigate(`/maintenance/work-orders/${encodeURIComponent(created.public_id)}`);
            }
            return created;
          }}
        />
      ) : null}
    </div>
  );
}
