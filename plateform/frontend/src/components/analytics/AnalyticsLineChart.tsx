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

import { formatChartBucket, formatNumber } from "../../lib/format";
import type { AnalyticsRange, TimeSeriesPoint } from "../../types/analytics";

interface SeriesConfig {
  key: string;
  name: string;
  color: string;
  unit: string;
  yAxisId?: "left" | "right";
  digits?: number;
}

interface AnalyticsLineChartProps {
  data: Array<Record<string, string | number | null>>;
  range: AnalyticsRange;
  series: SeriesConfig[];
}

export function AnalyticsLineChart({ data, range: _range, series }: AnalyticsLineChartProps) {
  void _range;
  const reduceMotion = useReducedMotion();
  const hasRight = series.some((item) => item.yAxisId === "right");

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="time"
          tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
        />
        <YAxis
          yAxisId="left"
          tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={46}
        />
        {hasRight ? (
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={46}
          />
        ) : null}
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--border)",
            boxShadow: "none",
          }}
          formatter={(value, name) => {
            const config = series.find((item) => item.name === name);
            if (value === null || value === undefined) {
              return ["Unavailable", name];
            }
            const numeric = typeof value === "number" ? value : Number(value);
            return [`${formatNumber(numeric, config?.digits ?? 1)} ${config?.unit ?? ""}`.trim(), name];
          }}
          labelFormatter={(label) => String(label)}
        />
        <Legend />
        {series.map((item) => (
          <Line
            key={item.key}
            yAxisId={item.yAxisId ?? "left"}
            type="monotone"
            dataKey={item.key}
            name={item.name}
            stroke={item.color}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={!reduceMotion}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function toChartRows(
  points: TimeSeriesPoint[],
  range: AnalyticsRange,
  keys: Array<keyof TimeSeriesPoint>,
): Array<Record<string, string | number | null>> {
  return points.map((point) => {
    const row: Record<string, string | number | null> = {
      time: formatChartBucket(point.timestamp, range),
    };
    for (const key of keys) {
      const value = point[key];
      row[String(key)] = typeof value === "string" || value === undefined ? null : value;
    }
    return row;
  });
}
