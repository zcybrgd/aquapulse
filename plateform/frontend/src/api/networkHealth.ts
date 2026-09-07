import { apiClient } from "./client";
import type {
  BulkRefreshResponse,
  DeviceNetworkDetail,
  DeviceNetworkHistoryItem,
  DeviceNetworkListResponse,
  DeviceNetworkSummary,
  IncidentDeviceNetworkContext,
  NetworkFilters,
} from "../types/networkHealth";

function toQuery(filters: NetworkFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.search.trim()) query.search = filters.search.trim();
  if (filters.zone.trim()) query.zone = filters.zone.trim();
  if (filters.asset_type.trim()) query.asset_type = filters.asset_type.trim();
  if (filters.reachability.trim()) query.reachability = filters.reachability.trim();
  if (filters.location_available.trim()) query.location_available = filters.location_available.trim();
  if (filters.cellular_available.trim()) query.cellular_available = filters.cellular_available.trim();
  if (filters.source_mode.trim()) query.source_mode = filters.source_mode.trim();
  return query;
}

export async function fetchNetworkSummary(
  filters: NetworkFilters,
  options?: { signal?: AbortSignal },
): Promise<DeviceNetworkSummary> {
  const { data } = await apiClient.get<DeviceNetworkSummary>("/api/network-health/summary", {
    params: toQuery(filters),
    signal: options?.signal,
  });
  return data;
}

export async function fetchNetworkDevices(
  filters: NetworkFilters,
  options?: { signal?: AbortSignal },
): Promise<DeviceNetworkListResponse> {
  const { data } = await apiClient.get<DeviceNetworkListResponse>("/api/network-health/devices", {
    params: toQuery(filters),
    signal: options?.signal,
  });
  return data;
}

export async function fetchNetworkDevice(assetId: string): Promise<DeviceNetworkDetail> {
  const { data } = await apiClient.get<DeviceNetworkDetail>(
    `/api/network-health/devices/${encodeURIComponent(assetId)}`,
  );
  return data;
}

export async function fetchNetworkDeviceHistory(assetId: string): Promise<DeviceNetworkHistoryItem[]> {
  const { data } = await apiClient.get<DeviceNetworkHistoryItem[]>(
    `/api/network-health/devices/${encodeURIComponent(assetId)}/history`,
  );
  return data;
}

export async function refreshNetworkDevice(
  assetId: string,
  force = false,
): Promise<DeviceNetworkDetail> {
  const { data } = await apiClient.post<DeviceNetworkDetail>(
    `/api/network-health/devices/${encodeURIComponent(assetId)}/refresh`,
    { force },
    { timeout: 20000 },
  );
  return data;
}

export async function refreshNetworkDevices(force = false): Promise<BulkRefreshResponse> {
  const { data } = await apiClient.post<BulkRefreshResponse>(
    "/api/network-health/refresh",
    { force, limit: 20 },
    { timeout: 25000 },
  );
  return data;
}

export async function fetchIncidentDeviceNetwork(
  incidentId: string,
  options?: { signal?: AbortSignal },
): Promise<IncidentDeviceNetworkContext> {
  const { data } = await apiClient.get<IncidentDeviceNetworkContext>(
    `/api/incidents/${encodeURIComponent(incidentId)}/device-network`,
    { signal: options?.signal },
  );
  return data;
}

export async function refreshIncidentDeviceNetwork(
  incidentId: string,
  force = false,
): Promise<IncidentDeviceNetworkContext> {
  const { data } = await apiClient.post<IncidentDeviceNetworkContext>(
    `/api/incidents/${encodeURIComponent(incidentId)}/device-network/refresh`,
    { force },
    { timeout: 20000 },
  );
  return data;
}
