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

import { formatChartTime } from "../../lib/format";
import type { DetectionDetail } from "../../types/detections";
import type { TelemetryHistoryResponse } from "../../types/telemetry";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";

interface DetectionEvidenceChartProps {
  detection: DetectionDetail;
  history: TelemetryHistoryResponse | null;
}

function thresholdFor(metric: string, detection: DetectionDetail): number | null {
  const match = detection.evidence.find((item) => item.metric === metric && item.threshold_value != null);
  return match?.threshold_value ?? null;
}

export function DetectionEvidenceChart({ detection, history }: DetectionEvidenceChartProps) {
  const items = history?.items ?? [];
  const chartData = items.map((item) => ({
    time: formatChartTime(item.time),
    iso: item.time,
    pressure: item.pressure_kpa,
    flow: item.flow_lps,
    signal: item.signal_strength_dbm,
    packetLoss: item.packet_loss_pct,
  }));
  const pressureThreshold = thresholdFor("pressure_kpa", detection);
  const packetThreshold = thresholdFor("packet_loss_pct", detection);

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Telemetry evidence</h3>
      <p className="mt-0.5 text-sm text-ink-muted">
        Window {formatChartTime(detection.window_start)} – {formatChartTime(detection.window_end)} UTC-local display.
        Units: pressure kPa, flow L/s, signal dBm, packet loss %.
      </p>
      {chartData.length === 0 ? (
        <EmptyState
          title="No readings in this window"
          description="The detection references a TimescaleDB window that currently has no points."
        />
      ) : (
        <div className="mt-4 h-80 min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e3ecef" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <ReferenceLine
                yAxisId="left"
                x={formatChartTime(detection.detected_at)}
                stroke="#e5484d"
                label="Detected"
              />
              {pressureThreshold != null ? (
                <ReferenceLine yAxisId="left" y={pressureThreshold} stroke="#f59e0b" strokeDasharray="4 4" />
              ) : null}
              {packetThreshold != null ? (
                <ReferenceLine yAxisId="right" y={packetThreshold} stroke="#647780" strokeDasharray="4 4" />
              ) : null}
              <Line yAxisId="left" type="monotone" dataKey="pressure" name="Pressure kPa" stroke="#08a6a6" dot={false} />
              <Line yAxisId="left" type="monotone" dataKey="flow" name="Flow L/s" stroke="#0b2436" dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="signal" name="Signal dBm" stroke="#2dd4bf" dot={false} />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="packetLoss"
                name="Packet loss %"
                stroke="#e5484d"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
