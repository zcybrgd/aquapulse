import type { AssetType } from "../types/assets";
import type { MapFilters, MapLayerVisibility } from "../types/map";

export const DEFAULT_MAP_LAYERS: MapLayerVisibility = {
  zones: true,
  pipelines: true,
  sensors: true,
  valves: true,
  gateways: true,
  incidents: true,
  detections: false,
};

export function emptyMapFilters(): MapFilters {
  return {
    zone: "",
    asset_type: "",
    asset_status: "",
    incident_severity: "",
    incident_status: "",
    include_resolved: false,
  };
}

export const MAP_TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

export const MAP_TILE_ATTRIBUTION =
  import.meta.env.VITE_MAP_ATTRIBUTION ?? "&copy; OpenStreetMap contributors";

export function pipelineColor(status: string, _criticality: number): string {
  const lowered = status.toLowerCase();
  if (lowered.includes("isolated") || lowered.includes("critical")) {
    return "#E5484D";
  }
  if (lowered.includes("degraded") || lowered.includes("maintenance")) {
    return "#F59E0B";
  }
  return "#08A6A6";
}

export function incidentColor(severity: string): string {
  if (severity === "tier_3") {
    return "#E5484D";
  }
  if (severity === "tier_2") {
    return "#F59E0B";
  }
  return "#08A6A6";
}

export function assetMatchesLayer(assetType: AssetType, layers: MapLayerVisibility): boolean {
  if (assetType === "sensor") {
    return layers.sensors;
  }
  if (assetType === "valve") {
    return layers.valves;
  }
  return layers.gateways;
}
