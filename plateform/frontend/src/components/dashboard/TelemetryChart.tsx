import { motion, useReducedMotion } from "framer-motion";
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

import type { TelemetryReading } from "../../types/api";
import type { TelemetryRange } from "../../types/telemetry";
import { formatChartTime, formatNumber } from "../../lib/format";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";

const ranges: Array<{ label: string; value: TelemetryRange }> = [
  { label: "Last hour", value: "1h" },
  { label: "Last 6 hours", value: "6h" },
  { label: "Last 24 hours", value: "24h" },
];

interface TelemetryChartProps {
  readings: TelemetryReading[];
  range: TelemetryRange;
  onRangeChange: (range: TelemetryRange) => void;
}

export function TelemetryChart({ readings, range, onRangeChange }: TelemetryChartProps) {
  const reduceMotion = useReducedMotion();

  const chartData = readings.map((reading) => ({
    time: formatChartTime(reading.timestamp),
    pressure: reading.pressure,
    flowRate: reading.flow_rate,
  }));

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: 0.12, ease: "easeOut" }}
    >
      <Card className="min-w-0 p-5">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-ink">Network telemetry</h3>
            <p className="mt-0.5 text-sm text-ink-muted">
              Simulated pressure and flow for the selected window
            </p>
          </div>
          <div className="flex flex-wrap gap-1 rounded-xl bg-page p-1" role="tablist" aria-label="Time range">
            {ranges.map((item) => (
              <button
                key={item.value}
                type="button"
                role="tab"
                aria-selected={range === item.value}
                onClick={() => onRangeChange(item.value)}
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  range === item.value
                    ? "bg-white text-ink shadow-sm"
                    : "text-ink-muted hover:text-ink"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {chartData.length === 0 ? (
          <EmptyState
            title="No simulated readings in this window"
            description="Historical seed covers 24 hours ending at the demo clock. Run the development simulator for newer points, or choose a wider range."
          />
        ) : (
          <div className="h-72 min-w-0">
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
                  yAxisId="pressure"
                  domain={["dataMin - 0.15", "dataMax + 0.15"]}
                  tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={42}
                  tickFormatter={(value: number) => formatNumber(value, 1)}
                />
                <YAxis
                  yAxisId="flow"
                  orientation="right"
                  tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                  tickFormatter={(value: number) => formatNumber(value, 0)}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid var(--border)",
                    boxShadow: "none",
                  }}
                  formatter={(value, name) => {
                    const numeric = typeof value === "number" ? value : Number(value);
                    if (name === "Pressure") {
                      return [`${formatNumber(numeric, 2)} bar`, name];
                    }
                    return [`${formatNumber(numeric, 1)} m³/h`, name];
                  }}
                />
                <Legend />
                <Line
                  yAxisId="pressure"
                  type="monotone"
                  dataKey="pressure"
                  name="Pressure"
                  stroke="var(--teal)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={!reduceMotion}
                  activeDot={{ r: 4 }}
                />
                <Line
                  yAxisId="flow"
                  type="monotone"
                  dataKey="flowRate"
                  name="Flow rate"
                  stroke="var(--navy)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={!reduceMotion}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </motion.div>
  );
}
