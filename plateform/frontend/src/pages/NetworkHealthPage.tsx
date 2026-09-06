import { useState } from "react";
import { RefreshCw } from "lucide-react";

import { fetchNetworkEvent } from "../api/networkHealth";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useNetworkHealthData } from "../hooks/useNetworkHealthData";
import { useNetworkHealthFilters } from "../hooks/useNetworkHealthFilters";
import { formatDateTime, formatNumber } from "../lib/format";
import type { NetworkEventDetail } from "../types/networkHealth";

const EVENT_TYPES = ["connectivity_check", "qod_requested", "qod_granted", "qod_denied", "qod_released", "agent_error"];

export function NetworkHealthPage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useNetworkHealthFilters();
  const { summary, events, loading, refreshing, error, updatedAt, reload } = useNetworkHealthData(filters);
  const [selected, setSelected] = useState<NetworkEventDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  async function openEvent(eventId: string) {
    setDetailError(null);
    try {
      setSelected(await fetchNetworkEvent(eventId));
    } catch {
      setSelected(null);
      setDetailError("That mock network event was not found.");
    }
  }

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Network Health</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Mock Network Agent logs — final contract pending. AquaPulse does not calculate network
            policy from these records.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Badge className="bg-warning/15 text-ink">Mock agent data</Badge>
          <Badge className="bg-page text-ink">Network Agent contract awaiting team confirmation</Badge>
          <p className="text-ink-muted">Updated {updatedAt ? formatDateTime(updatedAt.toISOString()) : "—"}</p>
          <Button variant="secondary" onClick={reload} disabled={loading || refreshing}>
            <RefreshCw size={14} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      <Card className="border-warning/30 p-4">
        <p className="text-sm font-medium text-ink">Contract status: Awaiting confirmation</p>
        <p className="mt-1 text-sm text-ink-muted">
          These labels are provisional presentation values, not a finalized Network Agent contract.
        </p>
      </Card>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Event type
          <select
            value={filters.event_type}
            onChange={(event) => setFilters({ event_type: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All types</option>
            {EVENT_TYPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Status
          <select
            value={filters.status}
            onChange={(event) => setFilters({ status: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Cluster
          <input
            value={filters.cluster}
            onChange={(event) => setFilters({ cluster: event.target.value })}
            placeholder="cluster-desert-042"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Device
          <input
            value={filters.device}
            onChange={(event) => setFilters({ device: event.target.value })}
            placeholder="valve-neom-north-01"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Incident
          <input
            value={filters.incident}
            onChange={(event) => setFilters({ incident: event.target.value })}
            placeholder="INC-1835"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Search
          <input
            value={filters.search}
            onChange={(event) => setFilters({ search: event.target.value })}
            placeholder="Event ID or summary"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          From
          <input
            type="datetime-local"
            value={filters.start}
            onChange={(event) => setFilters({ start: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          To
          <input
            type="datetime-local"
            value={filters.end}
            onChange={(event) => setFilters({ end: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
      </div>
      {hasActiveFilters ? (
        <Button variant="ghost" onClick={clearFilters}>
          Clear filters
        </Button>
      ) : null}

      {loading ? <Skeleton className="h-32 w-full" /> : null}
      {!loading && error ? <ErrorState title="Unable to load network logs" message={error} onRetry={reload} /> : null}

      {summary ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {[
            ["Connectivity checks", summary.connectivity_checks],
            ["Grants", summary.grants],
            ["Denials", summary.denials],
            ["Releases", summary.releases],
            ["Errors", summary.errors],
          ].map(([label, value]) => (
            <Card key={String(label)} className="min-w-0 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{formatNumber(Number(value), 0)}</p>
            </Card>
          ))}
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Latest event</p>
            <p className="mt-2 text-sm font-semibold text-ink">
              {summary.latest_event_at ? formatDateTime(summary.latest_event_at) : "—"}
            </p>
          </Card>
        </div>
      ) : null}

      {!loading && events && events.items.length === 0 ? (
        <EmptyState title="No mock network logs" description="No Network Agent draft events match these filters." />
      ) : null}

      {events && events.items.length > 0 ? (
        <Card className="min-w-0 overflow-x-auto p-0">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-page text-ink-muted">
              <tr>
                {["Event", "Type", "Status", "Cluster / device", "Incident", "Time"].map((head) => (
                  <th key={head} className="px-4 py-3 font-medium">
                    {head}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.items.map((item) => (
                <tr
                  key={item.id}
                  className="cursor-pointer border-t border-line hover:bg-page"
                  onClick={() => void openEvent(item.event_id)}
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink">{item.event_id}</p>
                    <p className="text-ink-muted">{item.summary}</p>
                  </td>
                  <td className="px-4 py-3">{item.event_type}</td>
                  <td className="px-4 py-3">{item.status}</td>
                  <td className="px-4 py-3">
                    {item.cluster_id ?? "—"}
                    <br />
                    <span className="text-ink-muted">{item.device_id ?? "—"}</span>
                  </td>
                  <td className="px-4 py-3">{item.incident_id ?? "—"}</td>
                  <td className="px-4 py-3">{formatDateTime(item.occurred_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}

      {detailError ? <p className="text-sm text-critical">{detailError}</p> : null}
      {selected ? (
        <Card className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-ink">{selected.event_id}</h3>
              <p className="text-sm text-ink-muted">{selected.summary}</p>
            </div>
            <Button variant="ghost" onClick={() => setSelected(null)}>
              Close
            </Button>
          </div>
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium text-ink">Sanitized payload</summary>
            <pre className="mt-2 max-h-72 overflow-auto rounded-xl bg-page p-3 text-xs text-ink">
              {JSON.stringify(selected.payload, null, 2)}
            </pre>
          </details>
        </Card>
      ) : null}
    </div>
  );
}
