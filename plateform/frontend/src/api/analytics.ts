import { apiClient } from "./client";
import type {
  AnalyticsAssetsResponse,
  AnalyticsBundle,
  AnalyticsDetectionsResponse,
  AnalyticsFilters,
  AnalyticsIncidentsResponse,
  AnalyticsOperationsResponse,
  AnalyticsOverviewResponse,
  AnalyticsTelemetryResponse,
  AnalyticsZonesResponse,
} from "../types/analytics";

const ANALYTICS_TIMEOUT = 20_000;

function toQuery(filters: AnalyticsFilters): Record<string, string> {
  const query: Record<string, string> = { range: filters.range };
  if (filters.zone.trim()) query.zone = filters.zone.trim();
  if (filters.sensor.trim()) query.sensor = filters.sensor.trim();
  return query;
}

export async function fetchAnalyticsOverview(
  filters: AnalyticsFilters,
  options?: { signal?: AbortSignal },
): Promise<AnalyticsOverviewResponse> {
  const { data } = await apiClient.get<AnalyticsOverviewResponse>("/api/analytics/overview", {
    params: toQuery(filters),
    signal: options?.signal,
    timeout: ANALYTICS_TIMEOUT,
  });
  return data;
}

export async function fetchAnalyticsBundle(
  filters: AnalyticsFilters,
  options?: { signal?: AbortSignal },
): Promise<AnalyticsBundle> {
  const params = toQuery(filters);
  const config = { params, signal: options?.signal, timeout: ANALYTICS_TIMEOUT };
  const [overview, telemetry, zones, detections, incidents, operations, assets] = await Promise.all([
    apiClient.get<AnalyticsOverviewResponse>("/api/analytics/overview", config),
    apiClient.get<AnalyticsTelemetryResponse>("/api/analytics/telemetry", config),
    apiClient.get<AnalyticsZonesResponse>("/api/analytics/zones", config),
    apiClient.get<AnalyticsDetectionsResponse>("/api/analytics/detections", config),
    apiClient.get<AnalyticsIncidentsResponse>("/api/analytics/incidents", config),
    apiClient.get<AnalyticsOperationsResponse>("/api/analytics/operations", config),
    apiClient.get<AnalyticsAssetsResponse>("/api/analytics/assets", config),
  ]);
  return {
    overview: overview.data,
    telemetry: telemetry.data,
    zones: zones.data,
    detections: detections.data,
    incidents: incidents.data,
    operations: operations.data,
    assets: assets.data,
  };
}
