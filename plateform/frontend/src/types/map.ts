import type { Feature, FeatureCollection, LineString, MultiPolygon, Point } from "geojson";

import type { AssetType, OperationalStatus } from "./assets";
import type { IncidentClassification, IncidentStatus, SeverityTier } from "./incidents";
import type { FreshnessState } from "./telemetry";

export interface ZoneFeatureProperties {
  code: string;
  name: string;
  country: string;
  region: string;
  asset_count: number;
  active_incident_count: number;
}

export interface PipelineFeatureProperties {
  external_id: string;
  name: string;
  status: string;
  criticality: number;
  zone: string;
  population_served: number;
  active_incident_count: number;
  connected_asset_count: number;
}

export interface AssetFeatureProperties {
  external_id: string;
  name: string;
  asset_type: AssetType;
  operational_status: OperationalStatus;
  health_score: number | null;
  zone: string;
  zone_id: string | null;
  location_label: string | null;
  has_cellular_identity: boolean;
  device_msisdn_masked: string | null;
  pipeline_segment: string | null;
  active_incident_count: number;
  last_seen_at: string | null;
  latest_reading_at: string | null;
  telemetry_freshness: FreshnessState | null;
  latest_packet_loss_pct: number | null;
  latest_signal_strength_dbm: number | null;
  latest_battery_pct: number | null;
}

export interface IncidentFeatureProperties {
  incident_number: string;
  title: string;
  severity: SeverityTier;
  classification: IncidentClassification;
  status: IncidentStatus;
  detected_at: string;
  related_asset_id: string | null;
  related_segment_id: string | null;
  summary: string | null;
}

export interface DetectionFeatureProperties {
  detection_number: string;
  priority: string;
  status: string;
  anomaly_score: number;
  trigger_reason: string;
  rule_code: string;
  sensor_id: string;
  zone: string;
  detected_at: string;
  data_mode: string;
}

export type ZoneFeature = Feature<MultiPolygon, ZoneFeatureProperties>;
export type PipelineFeature = Feature<LineString, PipelineFeatureProperties>;
export type AssetFeature = Feature<Point, AssetFeatureProperties>;
export type IncidentFeature = Feature<Point, IncidentFeatureProperties>;
export type DetectionFeature = Feature<Point, DetectionFeatureProperties>;

export type ZoneCollection = FeatureCollection<MultiPolygon, ZoneFeatureProperties>;
export type PipelineCollection = FeatureCollection<LineString, PipelineFeatureProperties>;
export type AssetCollection = FeatureCollection<Point, AssetFeatureProperties>;
export type IncidentCollection = FeatureCollection<Point, IncidentFeatureProperties>;
export type DetectionCollection = FeatureCollection<Point, DetectionFeatureProperties>;

export interface MapSummary {
  visible_zones: number;
  visible_pipelines: number;
  visible_assets: number;
  online: number;
  degraded: number;
  offline: number;
  active_incidents: number;
  critical_incidents: number;
  last_data_update: string | null;
  data_mode: "seeded_demo";
}

export interface NearbyItem {
  feature_type: "asset" | "pipeline" | "incident";
  id: string;
  name: string;
  distance_m: number;
  geometry: Point | LineString | MultiPolygon;
  properties: AssetFeatureProperties | PipelineFeatureProperties | IncidentFeatureProperties;
}

export interface NearbyResponse {
  origin: { latitude: number; longitude: number };
  radius_m: number;
  items: NearbyItem[];
  total: number;
}

export interface MapFilters {
  zone: string;
  asset_type: AssetType | "";
  asset_status: OperationalStatus | "";
  incident_severity: SeverityTier | "";
  incident_status: IncidentStatus | "";
  include_resolved: boolean;
}

export interface MapLayerVisibility {
  zones: boolean;
  pipelines: boolean;
  sensors: boolean;
  valves: boolean;
  gateways: boolean;
  incidents: boolean;
  detections: boolean;
}

export type MapSelection =
  | { kind: "asset"; feature: AssetFeature }
  | { kind: "pipeline"; feature: PipelineFeature }
  | { kind: "incident"; feature: IncidentFeature }
  | { kind: "detection"; feature: DetectionFeature }
  | { kind: "zone"; feature: ZoneFeature }
  | null;
