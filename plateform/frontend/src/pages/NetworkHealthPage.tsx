import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { fetchNetworkDevice, refreshNetworkDevice } from "../api/networkHealth";
import { NetworkDeviceDrawer } from "../components/network/NetworkDeviceDrawer";
import { ReachabilityBadge, SourceModeBadge } from "../components/network/ReachabilityBadge";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useNetworkHealthData } from "../hooks/useNetworkHealthData";
import { useNetworkHealthFilters } from "../hooks/useNetworkHealthFilters";
import { formatDateTime, formatNumber } from "../lib/format";
import type { DeviceNetworkDetail } from "../types/networkHealth";

const SELECT_CLASS = "h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink";

export function NetworkHealthPage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useNetworkHealthFilters();
  const { summary, devices, loading, refreshing, error, updatedAt, refreshAll } =
    useNetworkHealthData(filters);
  const [selected, setSelected] = useState<DeviceNetworkDetail | null>(null);
  const [detailRefreshing, setDetailRefreshing] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (!filters.device) {
      setSelected(null);
      return;
    }
    let cancelled = false;
    void fetchNetworkDevice(filters.device)
      .then((device) => {
        if (!cancelled) {
          setSelected(device);
          setDetailError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSelected(null);
          setDetailError("That device was not found.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [filters.device]);

  async function openDevice(assetId: string) {
    setFilters({ device: assetId });
  }

  async function refreshSelected() {
    if (!selected) return;
    setDetailRefreshing(true);
    try {
      setSelected(await refreshNetworkDevice(selected.asset_id, false));
      setDetailError(null);
    } catch {
      setDetailError("This device could not be refreshed.");
    } finally {
      setDetailRefreshing(false);
    }
  }

  const lastRefresh = summary?.last_refresh_at ?? devices?.last_refresh_at ?? null;
  const networkConnected =
    summary?.source_mode === "nokia_live" || summary?.source_mode === "nokia_simulator";
  const selectedZone =
    (summary?.available_zones ?? []).find(
      (zone) =>
        zone.toLowerCase() === filters.zone.toLowerCase() ||
        zone.toLowerCase().includes(filters.zone.trim().toLowerCase()),
    ) ?? filters.zone;

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Network Health</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Nokia/CAMARA connectivity for AquaPulse devices. The Network Agent is not part of this
            integration.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {summary ? <SourceModeBadge mode={summary.source_mode} label={summary.data_source_label} /> : null}
          {summary ? <Badge className="bg-page text-ink">{summary.environment_label}</Badge> : null}
          <p className="text-ink-muted">
            Last refresh {lastRefresh ? formatDateTime(lastRefresh) : updatedAt ? formatDateTime(updatedAt.toISOString()) : "—"}
          </p>
          <Button variant="secondary" onClick={() => void refreshAll()} disabled={loading || refreshing}>
            <RefreshCw size={14} aria-hidden="true" />
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Search
          <input
            value={filters.search}
            onChange={(event) => setFilters({ search: event.target.value })}
            placeholder="Device, zone, or masked identity"
            className={SELECT_CLASS}
          />
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Zone
          <select
            value={selectedZone}
            onChange={(event) => setFilters({ zone: event.target.value })}
            className={SELECT_CLASS}
          >
            <option value="">All zones</option>
            {(summary?.available_zones ?? []).map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Asset type
          <select
            value={filters.asset_type}
            onChange={(event) => setFilters({ asset_type: event.target.value })}
            className={SELECT_CLASS}
          >
            <option value="">All types</option>
            <option value="sensor">Sensor</option>
            <option value="valve">Valve</option>
            <option value="gateway">Gateway</option>
          </select>
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Reachability
          <select
            value={filters.reachability}
            onChange={(event) => setFilters({ reachability: event.target.value })}
            className={SELECT_CLASS}
          >
            <option value="">All</option>
            <option value="reachable">Reachable</option>
            <option value="unreachable">Unreachable</option>
            <option value="unknown_or_not_checked">Unknown / not checked</option>
            <option value="not_supported">No SIM</option>
          </select>
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Location available
          <select
            value={filters.location_available}
            onChange={(event) => setFilters({ location_available: event.target.value })}
            className={SELECT_CLASS}
          >
            <option value="">All</option>
            <option value="true">Available</option>
            <option value="false">Unavailable</option>
          </select>
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Cellular available
          <select
            value={filters.cellular_available}
            onChange={(event) => setFilters({ cellular_available: event.target.value })}
            className={SELECT_CLASS}
          >
            <option value="">All</option>
            <option value="true">Has SIM</option>
            <option value="false">No SIM</option>
          </select>
        </label>
        <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-ink-muted">
          Data source
          <select
            value={filters.source_mode}
            onChange={(event) => setFilters({ source_mode: event.target.value })}
            className={SELECT_CLASS}
          >
            <option value="">All sources</option>
            <option value="seeded_demo">Demonstration data</option>
            <option value="nokia_simulator">Nokia simulator</option>
            <option value="nokia_live">Nokia live</option>
          </select>
        </label>
      </div>
      {hasActiveFilters ? (
        <Button variant="ghost" onClick={clearFilters}>
          Clear filters
        </Button>
      ) : null}

      {loading ? <Skeleton className="h-32 w-full" /> : null}
      {!loading && error ? <ErrorState title="Unable to load network health" message={error} onRetry={() => void refreshAll()} /> : null}
      {!loading && !error && summary && !networkConnected ? (
        <EmptyState
          title="Network data source not connected"
          description="Nokia/CAMARA APIs are disabled. Device reachability and network-derived location stay unavailable until a trusted source is connected."
        />
      ) : null}

      {summary && networkConnected ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {[
            ["Cellular devices", summary.cellular_devices],
            ["Reachable", summary.reachable],
            ["Unreachable", summary.unreachable],
            ["Unknown / not checked", summary.unknown_or_not_checked],
            ["Network location available", summary.network_location_available],
            ["Stale checks", summary.stale_checks],
          ].map(([label, value]) => (
            <Card key={String(label)} className="min-w-0 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{formatNumber(Number(value), 0)}</p>
            </Card>
          ))}
        </div>
      ) : null}

      {networkConnected && !loading && devices && devices.items.length === 0 ? (
        <EmptyState title="No devices match" description="No AquaPulse devices match these network filters." />
      ) : null}

      {networkConnected && devices && devices.items.length > 0 ? (
        <>
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {devices.items.map((item) => (
              <Card key={item.asset_id} className="min-w-0 p-4">
                <button type="button" className="w-full text-left" onClick={() => void openDevice(item.asset_id)}>
                  <p className="font-semibold text-ink">{item.asset_id}</p>
                  <p className="text-sm text-ink-muted">{item.asset_name}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <ReachabilityBadge status={item.reachability_status} />
                    <SourceModeBadge mode={item.source_mode} label={item.data_source_label} />
                  </div>
                  <p className="mt-3 text-sm text-ink-muted">
                    {item.zone_name ?? "—"} · {item.has_cellular_identity ? item.device_msisdn_masked : "No SIM"}
                  </p>
                </button>
              </Card>
            ))}
          </div>

          <Card className="hidden min-w-0 overflow-x-auto p-0 md:block">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-page text-ink-muted">
                <tr>
                  {[
                    "Device",
                    "Type",
                    "Zone",
                    "Cellular identity",
                    "Reachability",
                    "Reachable via",
                    "Network-derived location",
                    "Accuracy",
                    "Last check",
                    "Data source",
                    "Action",
                  ].map((head) => (
                    <th key={head} className="whitespace-nowrap px-4 py-3 font-medium">
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {devices.items.map((item) => (
                  <tr key={item.asset_id} className="border-t border-line">
                    <td className="px-4 py-3">
                      <p className="font-medium text-ink">{item.asset_id}</p>
                      <p className="text-ink-muted">{item.asset_name}</p>
                    </td>
                    <td className="px-4 py-3 capitalize">{item.asset_type}</td>
                    <td className="px-4 py-3">{item.zone_name ?? "—"}</td>
                    <td className="px-4 py-3">
                      {item.has_cellular_identity ? item.device_msisdn_masked : "No SIM"}
                    </td>
                    <td className="px-4 py-3">
                      <ReachabilityBadge status={item.reachability_status} />
                    </td>
                    <td className="px-4 py-3 capitalize">{item.reachable_via ?? "—"}</td>
                    <td className="px-4 py-3">
                      {item.network_location_available &&
                      item.network_latitude != null &&
                      item.network_longitude != null
                        ? `${item.network_latitude.toFixed(4)}, ${item.network_longitude.toFixed(4)}`
                        : "Unavailable"}
                    </td>
                    <td className="px-4 py-3">
                      {item.accuracy_radius_m != null ? `${formatNumber(item.accuracy_radius_m, 0)} m` : "—"}
                    </td>
                    <td className="px-4 py-3">{item.retrieved_at ? formatDateTime(item.retrieved_at) : "—"}</td>
                    <td className="px-4 py-3">
                      <SourceModeBadge mode={item.source_mode} label={item.data_source_label} />
                    </td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" onClick={() => void openDevice(item.asset_id)}>
                        Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      ) : null}

      {detailError ? <p className="text-sm text-critical">{detailError}</p> : null}
      {selected ? (
        <NetworkDeviceDrawer
          device={selected}
          refreshing={detailRefreshing}
          onClose={() => setFilters({ device: "" })}
          onRefresh={() => void refreshSelected()}
        />
      ) : null}
    </div>
  );
}
