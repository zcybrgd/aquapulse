import type { IncidentClassification, IncidentStatus, SeverityTier } from "./incidents";

export type AssetType = "sensor" | "valve" | "gateway";

export type OperationalStatus = "online" | "degraded" | "offline";

export type ValvePosition = "open" | "closed" | "partial" | "unknown";

export type ControlMode = "manual" | "remote" | "automatic";

export type MaintenanceFilter = "due" | "upcoming" | "scheduled" | "";

export type AssetSortField =
  | "name"
  | "asset_type"
  | "status"
  | "health_score"
  | "last_seen"
  | "next_maintenance";

export type SortOrder = "asc" | "desc";

export interface AssetFilters {
  search: string;
  asset_type: AssetType | "";
  status: OperationalStatus | "";
  zone: string;
  maintenance: MaintenanceFilter;
  sort_by: AssetSortField;
  sort_order: SortOrder;
}

export interface AssetListSummary {
  total_assets: number;
  online: number;
  degraded: number;
  offline: number;
  maintenance_due: number;
}

export interface RelatedAssetIncident {
  id: string;
  incident_number: string;
  title: string;
  classification: IncidentClassification;
  severity: SeverityTier;
  status: IncidentStatus;
  detected_at: string;
}

export interface AssetSummary {
  id: string;
  external_id: string;
  name: string;
  asset_type: AssetType;
  operational_status: OperationalStatus;
  health_score: number | null;
  zone: string;
  zone_id: string;
  zone_name: string;
  location_label: string | null;
  has_cellular_identity: boolean;
  device_msisdn_masked: string | null;
  pipeline_segment: string | null;
  manufacturer: string | null;
  model: string | null;
  battery_pct: number | null;
  current_position: ValvePosition | null;
  last_seen_at: string | null;
  next_maintenance_at: string | null;
  maintenance_state: string;
}

export interface MeasurementRange {
  quantity: string;
  minimum: number;
  maximum: number;
  unit: string;
}

export interface SensorAttributes {
  measurement_types: string[];
  sampling_interval_seconds: number | null;
  battery_pct: number | null;
  signal_strength_dbm: number | null;
  calibration_date: string | null;
  measurement_ranges: MeasurementRange[];
  supported_units: string[];
}

export interface ValveAttributes {
  current_position: ValvePosition | null;
  control_mode: ControlMode | null;
  failsafe_position: string | null;
  actuation_type: string | null;
  last_command_at: string | null;
}

export interface GatewayAttributes {
  provider: string | null;
  connection_type: string | null;
  protocols: string[];
  signal_strength_dbm: number | null;
  packet_delivery_status: string | null;
}

export interface AssetDetail extends AssetSummary {
  serial_number: string | null;
  firmware_version: string | null;
  installed_at: string | null;
  commissioned_at: string | null;
  latitude: number | null;
  longitude: number | null;
  device_location: {
    zone_id: string;
    zone_name: string;
    location_label: string | null;
    latitude: number | null;
    longitude: number | null;
  };
  last_maintenance_at: string | null;
  control_mode: ControlMode | null;
  signal_strength_dbm: number | null;
  sampling_interval_seconds: number | null;
  sensor: SensorAttributes | null;
  valve: ValveAttributes | null;
  gateway: GatewayAttributes | null;
  related_incidents: RelatedAssetIncident[];
}

export interface AssetListResponse {
  items: AssetSummary[];
  total: number;
  summary: AssetListSummary;
}

export interface AssetIncidentListResponse {
  asset_id: string;
  items: RelatedAssetIncident[];
  total: number;
}

export interface AssetHealthPoint {
  timestamp: string;
  health_score: number;
  battery_pct: number | null;
  signal_strength_dbm: number | null;
  availability_pct: number | null;
  position_confirmed: boolean | null;
  packet_delivery_pct: number | null;
  pressure_kpa: number | null;
  flow_lps: number | null;
  packet_loss_pct: number | null;
  temperature_c: number | null;
}

export interface AssetHealthResponse {
  asset_id: string;
  series_kind: string;
  note: string;
  items: AssetHealthPoint[];
  range: string | null;
  freshness: "fresh" | "stale" | "offline" | null;
  last_reading_at: string | null;
  data_mode: string | null;
}
