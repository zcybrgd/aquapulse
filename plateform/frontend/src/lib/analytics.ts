import type { ComparedMetric, MetricInterpretation, TrendDirection, ZoneAnalyticsRow } from "../types/analytics";
import { formatNumber, formatSignedNumber } from "./format";

export const ANALYTICS_RANGES = [
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
] as const;

export const KPI_TOOLTIPS: Record<string, string> = {
  average_pressure: "Mean simulated pressure across selected sensors, shown in bar.",
  average_flow: "Mean simulated flow across selected sensors, shown in cubic metres per hour.",
  estimated_monitored_volume:
    "Estimated monitored volume integrates each simulated flow sample over 5 minutes. It is not confirmed consumption or water loss.",
  telemetry_completeness: "Share of expected 5-minute samples that were present in the selected window.",
  active_incidents: "Incidents that were still open at the end of the selected window.",
  mean_response_time:
    "Mean time from detection to recorded response start. Shown only when both timestamps exist.",
};

export function formatMetricValue(metric: ComparedMetric | undefined, digits = 1): string {
  if (!metric || metric.current === null) {
    return metric?.key?.includes("time") || metric?.unit === "min"
      ? "Not enough completed records"
      : "Unavailable";
  }
  const suffix = metric.unit ? ` ${metric.unit}` : "";
  return `${formatNumber(metric.current, digits)}${suffix}`;
}

export function formatComparison(metric: ComparedMetric | undefined): string {
  if (!metric) {
    return "No previous-period data";
  }
  if (metric.trend === "unavailable" || metric.previous === null) {
    return "No previous-period data";
  }
  const change =
    metric.change === null ? "" : formatSignedNumber(metric.change, metric.unit === "%" || metric.unit === "min" ? 1 : 2);
  const pct = metric.change_pct === null ? "" : ` (${formatSignedNumber(metric.change_pct, 1)}%)`;
  return `${change}${pct} vs previous period`;
}

export function trendTone(
  trend: TrendDirection,
  interpretation: MetricInterpretation,
): "default" | "up" | "down" | "muted" {
  if (trend === "unavailable" || trend === "stable") {
    return "muted";
  }
  if (interpretation === "neutral") {
    return "default";
  }
  if (interpretation === "higher_is_better") {
    return trend === "up" ? "up" : "down";
  }
  return trend === "down" ? "up" : "down";
}

export function csvEscape(value: string | number | null | boolean): string {
  const text = value === null ? "" : String(value);
  if (/[",\n]/.test(text)) {
    return `"${text.replaceAll("\"", "\"\"")}"`;
  }
  return text;
}

export function zoneRowsToCsv(
  rows: ZoneAnalyticsRow[],
  meta: { range: string; start: string; end: string; generatedAt: string; dataMode: string },
): string {
  const header = [
    "zone",
    "reporting_sensors",
    "telemetry_completeness_pct",
    "average_pressure_bar",
    "average_flow_m3h",
    "detection_count",
    "active_incident_count",
    "average_asset_health",
    "overdue_response_tasks",
    "sufficient_data",
    "range",
    "start",
    "end",
    "generated_at",
    "data_mode",
  ];
  const lines = [header.join(",")];
  for (const row of rows) {
    lines.push(
      [
        csvEscape(row.zone),
        csvEscape(row.reporting_sensors),
        csvEscape(row.telemetry_completeness_pct),
        csvEscape(row.average_pressure_bar),
        csvEscape(row.average_flow_m3h),
        csvEscape(row.detection_count),
        csvEscape(row.active_incident_count),
        csvEscape(row.average_asset_health),
        csvEscape(row.overdue_response_tasks),
        csvEscape(row.sufficient_data),
        csvEscape(meta.range),
        csvEscape(meta.start),
        csvEscape(meta.end),
        csvEscape(meta.generatedAt),
        csvEscape(meta.dataMode),
      ].join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

export function downloadTextFile(filename: string, contents: string, type = "text/csv;charset=utf-8") {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
