import { IncidentCenterHeader } from "../components/incidents/IncidentCenterHeader";
import { IncidentFiltersBar } from "../components/incidents/IncidentFiltersBar";
import { IncidentCardList, IncidentTable } from "../components/incidents/IncidentList";
import { IncidentListSkeleton } from "../components/incidents/IncidentListSkeleton";
import { IncidentSummaryCards } from "../components/incidents/IncidentSummaryCards";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { useIncidentFilters } from "../hooks/useIncidentFilters";
import { useIncidents } from "../hooks/useIncidents";

export function IncidentsPage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useIncidentFilters();
  const { items, total, stats, zones, loading, error, reload } = useIncidents(filters);

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      <IncidentCenterHeader stats={stats} ready={!loading && !error} />

      {loading ? <IncidentListSkeleton /> : null}

      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}

      {!loading && !error ? (
        <>
          <IncidentSummaryCards stats={stats} />
          <IncidentFiltersBar
            filters={filters}
            zones={zones}
            resultCount={total}
            hasActiveFilters={hasActiveFilters}
            onChange={setFilters}
            onClear={clearFilters}
          />
          {items.length === 0 ? (
            <div className="card">
              <EmptyState
                title="No incidents match these filters"
                description="Clear filters or try a different zone, severity or search term."
              />
            </div>
          ) : (
            <>
              <IncidentTable items={items} />
              <IncidentCardList items={items} />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
