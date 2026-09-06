export type AnalyticsRange = "24h" | "7d" | "30d";
export type AnalyticsInterval = "15m" | "30m" | "1h" | "6h" | "1d";
export type TrendDirection = "up" | "down" | "stable" | "unavailable";
export type MetricInterpretation = "higher_is_better" | "lower_is_better" | "neutral";

export interface AnalyticsFilters {
  range: AnalyticsRange;
  zone: string;
  sensor: string;
}

export interface AnalyticsFilterState {
  zone: string | null;
  sensor: string | null;
  interval: string | null;
}

export interface ComparedMetric {
  key: string;
  label: string;
  unit: string | null;
  current: number | null;
  previous: number | null;
  change: number | null;
  change_pct: number | null;
  trend: TrendDirection;
  interpretation: MetricInterpretation;
}

export interface NamedCount {
  key: string;
  label: string;
  count: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  pressure_bar: number | null;
  flow_m3h: number | null;
  packet_loss_pct: number | null;
  completeness_pct: number | null;
  reporting_sensors: number | null;
  reading_count: number | null;
  detections: number | null;
  incidents: number | null;
  mean_response_minutes: number | null;
}

export interface AnalyticsEnvelope {
  range: AnalyticsRange;
  start: string;
  end: string;
  generated_at: string;
  data_mode: "simulated";
  filters: AnalyticsFilterState;
}

export interface AnalyticsOverviewResponse extends AnalyticsEnvelope {
  kpis: ComparedMetric[];
  telemetry: Record<string, ComparedMetric>;
  events: Record<string, ComparedMetric>;
  operations: Record<string, ComparedMetric>;
  available_zones: string[];
  available_sensors: string[];
}

export interface AnalyticsTelemetryResponse extends AnalyticsEnvelope {
  interval: AnalyticsInterval;
  summary: Record<string, ComparedMetric>;
  series: TimeSeriesPoint[];
  reporting_sensors: number;
  stale_sensors: number;
  offline_sensors: number;
  selected_sensors: number;
}

export interface ZoneAnalyticsRow {
  zone: string;
  reporting_sensors: number;
  selected_sensors: number;
  telemetry_completeness_pct: number | null;
  average_pressure_bar: number | null;
  average_flow_m3h: number | null;
  detection_count: number;
  active_incident_count: number;
  average_asset_health: number | null;
  overdue_response_tasks: number;
  sufficient_data: boolean;
}

export interface AnalyticsZonesResponse extends AnalyticsEnvelope {
  items: ZoneAnalyticsRow[];
}

export interface AnalyticsDetectionsResponse extends AnalyticsEnvelope {
  interval: AnalyticsInterval;
  created: ComparedMetric;
  dismissed: ComparedMetric;
  promoted: ComparedMetric;
  promotion_rate: ComparedMetric;
  by_priority: NamedCount[];
  by_rule: NamedCount[];
  series: TimeSeriesPoint[];
}

export interface AnalyticsIncidentsResponse extends AnalyticsEnvelope {
  interval: AnalyticsInterval;
  created: ComparedMetric;
  resolved: ComparedMetric;
  false_alarms: ComparedMetric;
  by_severity: NamedCount[];
  by_classification: NamedCount[];
  by_status: NamedCount[];
  series: TimeSeriesPoint[];
}

export interface AnalyticsOperationsResponse extends AnalyticsEnvelope {
  interval: AnalyticsInterval;
  mean_acknowledgement_minutes: ComparedMetric;
  median_acknowledgement_minutes: ComparedMetric;
  mean_response_start_minutes: ComparedMetric;
  mean_resolution_minutes: ComparedMetric;
  open_response_tasks: ComparedMetric;
  completed_response_tasks: ComparedMetric;
  overdue_response_tasks: ComparedMetric;
  series: TimeSeriesPoint[];
}

export interface AssetHealthBucket {
  key: string;
  label: string;
  count: number;
}

export interface AnalyticsAssetsResponse extends AnalyticsEnvelope {
  health_bands: AssetHealthBucket[];
  operational_status: NamedCount[];
  connectivity: NamedCount[];
  average_health: number | null;
  sensor_count: number;
  total_assets: number;
}

export interface AnalyticsBundle {
  overview: AnalyticsOverviewResponse;
  telemetry: AnalyticsTelemetryResponse;
  zones: AnalyticsZonesResponse;
  detections: AnalyticsDetectionsResponse;
  incidents: AnalyticsIncidentsResponse;
  operations: AnalyticsOperationsResponse;
  assets: AnalyticsAssetsResponse;
}
