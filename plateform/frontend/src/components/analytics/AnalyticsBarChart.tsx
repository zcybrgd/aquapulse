import { useReducedMotion } from "framer-motion";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatNumber } from "../../lib/format";
import type { NamedCount } from "../../types/analytics";

interface AnalyticsBarChartProps {
  items: NamedCount[];
  unit?: string;
  color?: string;
}

export function AnalyticsBarChart({
  items,
  unit = "count",
  color = "var(--teal)",
}: AnalyticsBarChartProps) {
  const reduceMotion = useReducedMotion();
  const data = items.map((item) => ({ name: item.label, value: item.count }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: "var(--ink-muted)", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          interval={0}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: "var(--ink-muted)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--border)",
            boxShadow: "none",
          }}
          formatter={(value) => {
            const numeric = typeof value === "number" ? value : Number(value);
            return [`${formatNumber(numeric, 0)} ${unit}`, "Count"];
          }}
        />
        <Bar dataKey="value" fill={color} radius={[8, 8, 0, 0]} isAnimationActive={!reduceMotion} />
      </BarChart>
    </ResponsiveContainer>
  );
}
