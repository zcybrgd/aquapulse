import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";

import { AnalyticsBarChart } from "../components/analytics/AnalyticsBarChart";
import { AnalyticsChartCard } from "../components/analytics/AnalyticsChartCard";
import { AnalyticsKpiCard } from "../components/analytics/AnalyticsKpiCard";
import { AnalyticsLineChart, toChartRows } from "../components/analytics/AnalyticsLineChart";
import { ZoneTable } from "../components/analytics/ZoneTable";
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusDot } from "../components/ui/StatusDot";
import { useAnalyticsData } from "../hooks/useAnalyticsData";
import { useAnalyticsFilters } from "../hooks/useAnalyticsFilters";
import { ANALYTICS_RANGES } from "../lib/analytics";
import { formatDateTime } from "../lib/format";

export function AnalyticsPage() {
  const { filters, setFilters } = useAnalyticsFilters();
  const { data, loading, refreshing, error, updatedAt, reload } = useAnalyticsData(filters);
  const overview = data?.overview;
  const telemetryHasValues = Boolean(
    data?.telemetry.series.some((point) => point.pressure_bar !== null || point.flow_m3h !== null),
  );
  const qualityHasValues = Boolean(
    data?.telemetry.series.some((point) => point.packet_loss_pct !== null || point.completeness_pct !== null),
  );
  const responseHasValues = Boolean(
    data?.operations.series.some((point) => point.mean_response_minutes !== null),
  );

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Analytics</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Simulated telemetry and recorded operational response. Estimated monitored volume is not
            confirmed consumption or water loss. Analytics does not make operational decisions.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <StatusDot label="Simulated data" />
          <p className="text-ink-muted">
            Updated {updatedAt ? formatDateTime(updatedAt.toISOString()) : "—"}
          </p>
          <Button variant="secondary" onClick={reload} disabled={loading || refreshing}>
            <RefreshCw size={14} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-line bg-white p-3 sm:flex-row sm:flex-wrap sm:items-end">
        <div className="flex flex-wrap gap-1 rounded-xl bg-page p-1" role="tablist" aria-label="Analytics period">
          {ANALYTICS_RANGES.map((item) => (
            <button
              key={item.value}
              type="button"
              role="tab"
              aria-selected={filters.range === item.value}
              onClick={() => setFilters({ range: item.value })}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                filters.range === item.value ? "bg-white text-ink shadow-sm" : "text-ink-muted hover:text-ink"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <label className="flex min-w-[10rem] flex-1 flex-col gap-1 text-xs font-medium text-ink-muted">
          Zone
          <select
            value={filters.zone}
            onChange={(event) => setFilters({ zone: event.target.value, sensor: "" })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All zones</option>
            {(overview?.available_zones ?? []).map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-[10rem] flex-1 flex-col gap-1 text-xs font-medium text-ink-muted">
          Sensor
          <select
            value={filters.sensor}
            onChange={(event) => setFilters({ sensor: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All sensors</option>
            {(overview?.available_sensors ?? []).map((sensor) => (
              <option key={sensor} value={sensor}>
                {sensor}
              </option>
            ))}
          </select>
        </label>
        {filters.sensor ? (
          <Link to={`/assets/${encodeURIComponent(filters.sensor)}`} className="text-sm font-medium text-teal hover:underline">
            Open sensor
          </Link>
        ) : null}
      </div>

      {loading && !data ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
      ) : null}

      {error ? <ErrorState message={error} onRetry={reload} /> : null}

      {overview ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <AnalyticsKpiCard metric={kpi(overview.kpis, "average_pressure")} digits={2} />
          <AnalyticsKpiCard metric={kpi(overview.kpis, "average_flow")} digits={1} />
          <AnalyticsKpiCard metric={kpi(overview.kpis, "estimated_monitored_volume")} digits={0} />
          <AnalyticsKpiCard metric={kpi(overview.kpis, "telemetry_completeness")} digits={1} />
          <AnalyticsKpiCard
            metric={kpi(overview.kpis, "active_incidents")}
            href={`/incidents${filters.zone ? `?zone=${encodeURIComponent(filters.zone)}` : ""}`}
            digits={0}
          />
          <AnalyticsKpiCard metric={kpi(overview.kpis, "mean_response_time")} href="/operations" digits={1} />
        </div>
      ) : null}

      {data ? (
        <>
          <AnalyticsChartCard
            title="Pressure and flow"
            description="Simulated network pressure (bar) and flow (m³/h). Gaps are missing samples, not zeros."
            empty={!telemetryHasValues}
          >
            <AnalyticsLineChart
              range={filters.range}
              data={toChartRows(data.telemetry.series, filters.range, ["pressure_bar", "flow_m3h"])}
              series={[
                { key: "pressure_bar", name: "Pressure", color: "var(--teal)", unit: "bar", digits: 2 },
                { key: "flow_m3h", name: "Flow", color: "var(--navy)", unit: "m³/h", yAxisId: "right", digits: 1 },
              ]}
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="Telemetry quality"
            description="Average packet loss and reporting completeness for the selected window."
            empty={!qualityHasValues}
          >
            <AnalyticsLineChart
              range={filters.range}
              data={toChartRows(data.telemetry.series, filters.range, ["packet_loss_pct", "completeness_pct"])}
              series={[
                { key: "packet_loss_pct", name: "Packet loss", color: "var(--warning)", unit: "%", digits: 2 },
                {
                  key: "completeness_pct",
                  name: "Completeness",
                  color: "var(--teal)",
                  unit: "%",
                  yAxisId: "right",
                  digits: 1,
                },
              ]}
            />
          </AnalyticsChartCard>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <AnalyticsChartCard
              title="Potential anomalies by rule"
              description="Deterministic detections created in this period. A detection is not a confirmed incident."
              empty={data.detections.by_rule.length === 0}
              actions={
                <Link
                  to={`/detections${filters.zone ? `?zone=${encodeURIComponent(filters.zone)}` : ""}`}
                  className="text-sm font-medium text-teal hover:underline"
                >
                  Investigation Queue
                </Link>
              }
            >
              <AnalyticsBarChart items={data.detections.by_rule} />
            </AnalyticsChartCard>
            <AnalyticsChartCard
              title="Detections by priority"
              description="Priority is an investigation ranking, not a leak confirmation."
              empty={data.detections.by_priority.length === 0}
              actions={
                <Link to="/detections?priority=critical" className="text-sm font-medium text-teal hover:underline">
                  Critical queue
                </Link>
              }
            >
              <AnalyticsBarChart items={data.detections.by_priority} color="var(--navy)" />
            </AnalyticsChartCard>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <AnalyticsChartCard
              title="Incidents by severity"
              description="Recorded incidents created in the selected window."
              empty={data.incidents.by_severity.length === 0}
              actions={
                <Link
                  to={`/incidents${filters.zone ? `?zone=${encodeURIComponent(filters.zone)}` : ""}`}
                  className="text-sm font-medium text-teal hover:underline"
                >
                  Incident Center
                </Link>
              }
            >
              <AnalyticsBarChart items={data.incidents.by_severity} color="var(--critical)" />
            </AnalyticsChartCard>
            <AnalyticsChartCard
              title="Incidents by status"
              description="Current status of incidents detected in this period."
              empty={data.incidents.by_status.length === 0}
            >
              <AnalyticsBarChart items={data.incidents.by_status} />
            </AnalyticsChartCard>
          </div>

          <AnalyticsChartCard
            title="Recorded response-start time"
            description="Mean minutes from detection to recorded response start. Blank buckets have no completed timestamps."
            empty={!responseHasValues}
            actions={
              <Link to="/operations" className="text-sm font-medium text-teal hover:underline">
                Operations Center
              </Link>
            }
          >
            <AnalyticsLineChart
              range={filters.range}
              data={toChartRows(data.operations.series, filters.range, ["mean_response_minutes"])}
              series={[
                {
                  key: "mean_response_minutes",
                  name: "Mean response start",
                  color: "var(--navy)",
                  unit: "min",
                  digits: 1,
                },
              ]}
            />
          </AnalyticsChartCard>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <AnalyticsChartCard
              title="Asset-health distribution"
              description="Health bands from the asset registry. These scores are demonstration values."
              empty={data.assets.health_bands.every((item) => item.count === 0)}
              actions={
                <Link
                  to={`/assets${filters.zone ? `?zone=${encodeURIComponent(filters.zone)}` : ""}`}
                  className="text-sm font-medium text-teal hover:underline"
                >
                  Asset Registry
                </Link>
              }
            >
              <AnalyticsBarChart
                items={data.assets.health_bands.map((item) => ({
                  key: item.key,
                  label: item.label,
                  count: item.count,
                }))}
              />
            </AnalyticsChartCard>
            <AnalyticsChartCard
              title="Sensor connectivity"
              description="Fresh, stale and offline sensors measured against the frozen demonstration clock."
              empty={data.assets.connectivity.every((item) => item.count === 0)}
            >
              <AnalyticsBarChart items={data.assets.connectivity} color="var(--navy)" />
            </AnalyticsChartCard>
          </div>

          <ZoneTable payload={data.zones} />
        </>
      ) : null}
    </div>
  );
}

function kpi(items: Array<{ key: string }>, key: string) {
  return items.find((item) => item.key === key) as
    | import("../types/analytics").ComparedMetric
    | undefined;
}
