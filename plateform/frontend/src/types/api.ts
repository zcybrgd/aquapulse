export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  database: string;
  postgis: string;
  timescaledb: string;
}

export interface DashboardSummary {
  active_incidents: number;
  critical_incidents: number;
  online_sensors: number;
  total_sensors: number;
  network_health_percent: number | null;
  estimated_water_loss_m3: number | null;
  average_response_time_min: number | null;
  awaiting_approval?: number;
  responding?: number;
  overdue_response_tasks?: number;
}

export interface TelemetryReading {
  timestamp: string;
  pressure: number;
  flow_rate: number;
  packet_loss: number;
}

export interface TelemetryResponse {
  readings: TelemetryReading[];
  range: string;
  data_mode: "simulated";
  last_updated: string | null;
  network_health_percent: number | null;
}
