import { useReducedMotion } from "framer-motion";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatChartTime, formatNumber, formatPercent } from "../../lib/format";
import type { AssetHealthResponse, AssetType } from "../../types/assets";
import type { TelemetryRange } from "../../types/telemetry";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { FreshnessBadge, SimulatedTelemetryBadge } from "../telemetry/TelemetryBadges";
import { TelemetryStatusBar } from "../telemetry/TelemetryStatusBar";

const ranges: Array<{ label: string; value: TelemetryRange }> = [
  { label: "Last hour", value: "1h" },
  { label: "Last 6 hours", value: "6h" },
  { label: "Last 24 hours", value: "24h" },
];

interface AssetHealthChartProps {
  assetType: AssetType;
  health: AssetHealthResponse;
  range: TelemetryRange;
  onRangeChange: (range: TelemetryRange) => void;
  refreshing: boolean;
  lastRefreshAt: string | null;
  backgroundError: string | null;
  onRefresh: () => void;
}

export function AssetHealthChart({
  assetType,
  health,
  range,
  onRangeChange,
  refreshing,
  lastRefreshAt,
  backgroundError,
  onRefresh,
}: AssetHealthChartProps) {
  const reduceMotion = useReducedMotion();
  const isSensor = assetType === "sensor";
  const chartData = health.items.map((point) => ({
    time: formatChartTime(point.timestamp),
    health: point.health_score,
    battery: point.battery_pct,
    signal: point.signal_strength_dbm,
    availability: point.availability_pct,
    packet: point.packet_delivery_pct,
    pressure: point.pressure_kpa == null ? null : point.pressure_kpa * 0.01,
    flow: point.flow_lps == null ? null : point.flow_lps * 3.6,
    loss: point.packet_loss_pct,
  }));
  const latest = health.items.length > 0 ? health.items[health.items.length - 1] : null;

  return (
    <Card className="min-w-0 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-ink">
            {isSensor ? "Recent telemetry" : "Recent health"}
          </h3>
          <p className="mt-0.5 text-sm text-ink-muted">{health.note}</p>
        </div>
        {isSensor ? (
          <div className="flex flex-wrap items-center gap-2">
            {health.freshness ? <FreshnessBadge state={health.freshness} /> : null}
            <SimulatedTelemetryBadge />
          </div>
        ) : (
          <span className="rounded-full bg-page px-2.5 py-0.5 text-[11px] font-medium text-ink-muted">
            Recent health unavailable
          </span>
        )}
      </div>

      {isSensor ? (
        <>
          <div className="mt-4">
            <TelemetryStatusBar
              lastUpdated={health.last_reading_at}
              lastRefreshAt={lastRefreshAt}
              refreshing={refreshing}
              backgroundError={backgroundError}
              onRefresh={onRefresh}
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-1 rounded-xl bg-page p-1" role="tablist" aria-label="Health range">
            {ranges.map((item) => (
              <button
                key={item.value}
                type="button"
                role="tab"
                aria-selected={range === item.value}
                onClick={() => onRangeChange(item.value)}
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  range === item.value ? "bg-white text-ink shadow-sm" : "text-ink-muted hover:text-ink"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          {latest ? (
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-5">
              <Metric label="Pressure" value={latest.pressure_kpa == null ? "—" : `${formatNumber(latest.pressure_kpa * 0.01, 2)} bar`} />
              <Metric label="Flow" value={latest.flow_lps == null ? "—" : `${formatNumber(latest.flow_lps * 3.6, 1)} m³/h`} />
              <Metric label="Signal" value={latest.signal_strength_dbm == null ? "—" : `${latest.signal_strength_dbm} dBm`} />
              <Metric label="Packet loss" value={latest.packet_loss_pct == null ? "—" : formatPercent(latest.packet_loss_pct)} />
              <Metric label="Battery" value={latest.battery_pct == null ? "—" : formatPercent(latest.battery_pct)} />
            </dl>
          ) : null}
        </>
      ) : null}

      {chartData.length === 0 ? (
        <EmptyState
          title="No readings for this sensor"
          description="This sensor has no TimescaleDB readings in the selected window. Offline sensors stop reporting before the demo clock."
        />
      ) : (
        <div className="mt-5 h-72 min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="time"
                tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: "var(--border)" }}
              />
              <YAxis
                yAxisId="primary"
                domain={isSensor ? ["auto", "auto"] : [0, 100]}
                tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={36}
                tickFormatter={(value: number) => formatNumber(value, isSensor ? 1 : 0)}
              />
              {isSensor ? (
                <YAxis
                  yAxisId="secondary"
                  orientation="right"
                  tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={42}
                  tickFormatter={(value: number) => formatNumber(value, 0)}
                />
              ) : null}
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid var(--border)",
                  fontSize: 12,
                }}
              />
              <Legend />
              {isSensor ? (
                <>
                  <Line
                    yAxisId="primary"
                    type="monotone"
                    dataKey="pressure"
                    name="Pressure (bar)"
                    stroke="var(--teal)"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={!reduceMotion}
                  />
                  <Line
                    yAxisId="secondary"
                    type="monotone"
                    dataKey="flow"
                    name="Flow (m³/h)"
                    stroke="var(--navy)"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={!reduceMotion}
                  />
                </>
              ) : (
                <Line
                  yAxisId="primary"
                  type="monotone"
                  dataKey="health"
                  name="Health"
                  stroke="var(--teal)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              )}
              {assetType === "valve" ? (
                <Line
                  yAxisId="primary"
                  type="monotone"
                  dataKey="availability"
                  name="Availability %"
                  stroke="var(--navy)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              ) : null}
              {assetType === "gateway" ? (
                <Line
                  yAxisId="primary"
                  type="monotone"
                  dataKey="packet"
                  name="Packet delivery %"
                  stroke="var(--navy)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              ) : null}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl bg-page px-3 py-2">
      <dt className="text-[11px] text-ink-muted">{label}</dt>
      <dd className="truncate font-medium text-ink">{value}</dd>
    </div>
  );
}
