import type { AxiosRequestConfig } from "axios";

import { apiClient } from "./client";
import type {
  AssetCollection,
  IncidentCollection,
  DetectionCollection,
  MapFilters,
  MapSummary,
  NearbyResponse,
  PipelineCollection,
  ZoneCollection,
} from "../types/map";

export function toMapQuery(filters: MapFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.zone) {
    query.zone = filters.zone;
  }
  if (filters.asset_type) {
    query.asset_type = filters.asset_type;
  }
  if (filters.asset_status) {
    query.asset_status = filters.asset_status;
  }
  if (filters.incident_severity) {
    query.incident_severity = filters.incident_severity;
  }
  if (filters.incident_status) {
    query.incident_status = filters.incident_status;
  }
  if (filters.include_resolved) {
    query.include_resolved = "true";
  }
  return query;
}

export async function fetchMapZones(
  filters: MapFilters,
  config?: AxiosRequestConfig,
): Promise<ZoneCollection> {
  const { data } = await apiClient.get<ZoneCollection>("/api/map/zones", {
    params: toMapQuery(filters),
    ...config,
  });
  return data;
}

export async function fetchMapPipelines(
  filters: MapFilters,
  config?: AxiosRequestConfig,
): Promise<PipelineCollection> {
  const { data } = await apiClient.get<PipelineCollection>("/api/map/pipelines", {
    params: toMapQuery(filters),
    ...config,
  });
  return data;
}

export async function fetchMapAssets(
  filters: MapFilters,
  config?: AxiosRequestConfig,
): Promise<AssetCollection> {
  const { data } = await apiClient.get<AssetCollection>("/api/map/assets", {
    params: toMapQuery(filters),
    ...config,
  });
  return data;
}

export async function fetchMapIncidents(
  filters: MapFilters,
  config?: AxiosRequestConfig,
): Promise<IncidentCollection> {
  const { data } = await apiClient.get<IncidentCollection>("/api/map/incidents", {
    params: toMapQuery(filters),
    ...config,
  });
  return data;
}

export async function fetchMapDetections(
  filters: MapFilters,
  config?: AxiosRequestConfig,
): Promise<DetectionCollection> {
  const { data } = await apiClient.get<DetectionCollection>("/api/map/detections", {
    params: toMapQuery(filters),
    ...config,
  });
  return data;
}

export async function fetchMapSummary(
  filters: MapFilters,
  config?: AxiosRequestConfig,
): Promise<MapSummary> {
  const { data } = await apiClient.get<MapSummary>("/api/map/summary", {
    params: toMapQuery(filters),
    ...config,
  });
  return data;
}

export async function fetchNearby(
  latitude: number,
  longitude: number,
  radius_m: number,
  featureType?: "asset" | "pipeline" | "incident",
  config?: AxiosRequestConfig,
): Promise<NearbyResponse> {
  const { data } = await apiClient.get<NearbyResponse>("/api/map/nearby", {
    params: {
      latitude,
      longitude,
      radius_m,
      ...(featureType ? { feature_type: featureType } : {}),
    },
    ...config,
  });
  return data;
}
