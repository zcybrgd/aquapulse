import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatChartTime, formatNumber, formatSignedNumber } from "../../lib/format";
import type { IncidentDetail } from "../../types/incidents";
import { Card } from "../ui/Card";

interface IncidentTelemetryChartProps {
  incident: IncidentDetail;
}

export function IncidentTelemetryChart({ incident }: IncidentTelemetryChartProps) {
  const chartData = incident.telemetry.map((point) => ({
    time: formatChartTime(point.timestamp),
    pressure: point.pressure,
    flowRate: point.flow_rate,
    isDetection: point.is_detection,
  }));
  const detection = chartData.find((point) => point.isDetection);

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Telemetry evidence</h3>
      <p className="mt-0.5 text-sm text-ink-muted">
        Pressure and flow around the detection marker for this incident
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-2xl bg-page px-3 py-2">
          <p className="text-xs text-ink-muted">Pressure change</p>
          <p className="mt-1 text-sm font-semibold text-ink">
            {formatSignedNumber(incident.pressure_change_bar, 2, "bar")}
          </p>
        </div>
        <div className="rounded-2xl bg-page px-3 py-2">
          <p className="text-xs text-ink-muted">Flow change</p>
          <p className="mt-1 text-sm font-semibold text-ink">
            {formatSignedNumber(incident.flow_change_m3h, 1, "m³/h")}
          </p>
        </div>
        <div className="rounded-2xl bg-page px-3 py-2">
          <p className="text-xs text-ink-muted">Estimated water loss</p>
          <p className="mt-1 text-sm font-semibold text-ink">
            {formatNumber(incident.estimated_water_loss_m3, 1)} m³
          </p>
        </div>
        <div className="rounded-2xl bg-page px-3 py-2">
          <p className="text-xs text-ink-muted">Packet loss</p>
          <p className="mt-1 text-sm font-semibold text-ink">
            {formatNumber(incident.packet_loss_percent, 1)}%
          </p>
        </div>
      </div>
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
            {detection ? (
              <ReferenceLine
                yAxisId="pressure"
                x={detection.time}
                stroke="var(--critical)"
                strokeDasharray="4 4"
                label={{ value: "Detected", fill: "var(--ink-muted)", fontSize: 11 }}
              />
            ) : null}
            <Line
              yAxisId="pressure"
              type="monotone"
              dataKey="pressure"
              name="Pressure"
              stroke="var(--teal)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="flow"
              type="monotone"
              dataKey="flowRate"
              name="Flow rate"
              stroke="var(--navy)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
