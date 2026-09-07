export type ReachabilityStatus =
  | "reachable"
  | "unreachable"
  | "unknown"
  | "not_supported"
  | "not_checked";

export type SourceMode = "seeded_demo" | "nokia_simulator" | "nokia_live";

export interface NetworkFilters {
  search: string;
  zone: string;
  asset_type: string;
  reachability: string;
  location_available: string;
  cellular_available: string;
  source_mode: string;
  device: string;
}

export interface LastTelemetry {
  observed_at: string | null;
  pressure_kpa: number | null;
  flow_lps: number | null;
  temperature_c: number | null;
}

export interface DeviceNetworkSnapshot {
  snapshot_id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  zone_id: string | null;
  zone_name: string | null;
  location_label: string | null;
  registered_latitude: number | null;
  registered_longitude: number | null;
  has_cellular_identity: boolean;
  device_msisdn_masked: string | null;
  reachability_status: ReachabilityStatus;
  reachable_via: string | null;
  reachability_checked_at: string | null;
  network_location_available: boolean;
  network_latitude: number | null;
  network_longitude: number | null;
  accuracy_radius_m: number | null;
  location_area_type: string | null;
  location_observed_at: string | null;
  location_offset_m: number | null;
  retrieved_at: string | null;
  stale: boolean;
  provider: string | null;
  source_mode: SourceMode | null;
  data_source_label: string;
  error_code: string | null;
  error_message: string | null;
  last_telemetry: LastTelemetry | null;
}

export interface DeviceNetworkHistoryItem {
  snapshot_id: string;
  reachability_status: ReachabilityStatus;
  reachable_via: string | null;
  network_location_available: boolean;
  network_latitude: number | null;
  network_longitude: number | null;
  accuracy_radius_m: number | null;
  retrieved_at: string;
  source_mode: SourceMode;
  error_code: string | null;
}

export interface DeviceNetworkDetail extends DeviceNetworkSnapshot {
  snapshot_public_id: string | null;
  request_correlation_id: string | null;
  cached: boolean;
  history: DeviceNetworkHistoryItem[];
}

export interface DeviceNetworkListResponse {
  items: DeviceNetworkSnapshot[];
  total: number;
  source_mode: SourceMode;
  data_source_label: string;
  last_refresh_at: string | null;
}

export interface DeviceNetworkSummary {
  cellular_devices: number;
  reachable: number;
  unreachable: number;
  unknown_or_not_checked: number;
  network_location_available: number;
  stale_checks: number;
  last_refresh_at: string | null;
  source_mode: SourceMode;
  data_source_label: string;
  environment_label: string;
  available_zones: string[];
  note: string;
}

export interface BulkRefreshResponse {
  requested: number;
  succeeded: number;
  failed: number;
  skipped_cached: number;
  items: DeviceNetworkSnapshot[];
  errors: { asset_id: string; error_code: string; error_message: string }[];
  source_mode: SourceMode;
  data_source_label: string;
  partial_success: boolean;
}

export interface IncidentDeviceNetworkContext {
  incident_id: string;
  asset_id: string | null;
  available: boolean;
  reachability_status: ReachabilityStatus | null;
  reachable_via: string | null;
  reachability_checked_at: string | null;
  network_location_available: boolean;
  network_latitude: number | null;
  network_longitude: number | null;
  accuracy_radius_m: number | null;
  registered_latitude: number | null;
  registered_longitude: number | null;
  location_offset_m: number | null;
  source_mode: SourceMode | null;
  data_source_label: string | null;
  device_msisdn_masked: string | null;
  note: string;
}
