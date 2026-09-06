export type TelemetryMetric =
  | "pressure"
  | "flow"
  | "temperature"
  | "signal"
  | "packet_loss"
  | "battery";

export type TelemetryRange = "1h" | "6h" | "24h" | "7d";

export type TelemetryInterval = "raw" | "1m" | "5m" | "15m" | "1h";

export type FreshnessState = "fresh" | "stale" | "offline";

export type TelemetryDataMode = "simulated";

export interface TelemetryReading {
  time: string;
  pressure_kpa: number | null;
  flow_lps: number | null;
  temperature_c: number | null;
  signal_strength_dbm: number | null;
  packet_loss_pct: number | null;
  battery_pct: number | null;
}

export interface TelemetryMetricUnit {
  metric: string;
  unit: string;
  display_unit: string;
}

export interface TelemetryHistoryResponse {
  sensor_id: string;
  name: string;
  range: string;
  start: string;
  end: string;
  interval: string;
  metrics: string[];
  units: TelemetryMetricUnit[];
  data_mode: TelemetryDataMode;
  items: TelemetryReading[];
  total: number;
}

export interface LatestTelemetryResponse {
  sensor_id: string;
  name: string;
  time: string | null;
  pressure_kpa: number | null;
  flow_lps: number | null;
  temperature_c: number | null;
  signal_strength_dbm: number | null;
  packet_loss_pct: number | null;
  battery_pct: number | null;
  freshness: FreshnessState;
  age_seconds: number | null;
  data_mode: TelemetryDataMode;
}

export interface NetworkTelemetrySummary {
  sensor_count: number;
  fresh_sensors: number;
  stale_sensors: number;
  offline_sensors: number;
  average_packet_delivery_pct: number | null;
  average_signal_strength_dbm: number | null;
  average_battery_pct: number | null;
  last_telemetry_at: string | null;
  data_mode: TelemetryDataMode;
}

export interface LatestTelemetryBatch {
  items: LatestTelemetryResponse[];
  total: number;
  data_mode: TelemetryDataMode;
  last_telemetry_at: string | null;
}
