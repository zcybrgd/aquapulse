import { apiClient } from "./client";
import type {
  AssetDetail,
  AssetFilters,
  AssetHealthResponse,
  AssetIncidentListResponse,
  AssetListResponse,
} from "../types/assets";

export function toAssetQuery(filters: AssetFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.search.trim()) {
    query.search = filters.search.trim();
  }
  if (filters.asset_type) {
    query.asset_type = filters.asset_type;
  }
  if (filters.status) {
    query.status = filters.status;
  }
  if (filters.zone) {
    query.zone = filters.zone;
  }
  if (filters.maintenance) {
    query.maintenance = filters.maintenance;
  }
  if (filters.sort_by) {
    query.sort_by = filters.sort_by;
  }
  if (filters.sort_order) {
    query.sort_order = filters.sort_order;
  }
  return query;
}

export async function fetchAssets(filters: AssetFilters): Promise<AssetListResponse> {
  const { data } = await apiClient.get<AssetListResponse>("/api/assets", {
    params: toAssetQuery(filters),
  });
  return data;
}

export async function fetchAsset(assetId: string): Promise<AssetDetail> {
  const { data } = await apiClient.get<AssetDetail>(
    `/api/assets/${encodeURIComponent(assetId)}`,
  );
  return data;
}

export async function fetchAssetIncidents(
  assetId: string,
): Promise<AssetIncidentListResponse> {
  const { data } = await apiClient.get<AssetIncidentListResponse>(
    `/api/assets/${encodeURIComponent(assetId)}/incidents`,
  );
  return data;
}

export async function fetchAssetHealth(
  assetId: string,
  range?: "1h" | "6h" | "24h" | "7d",
  config: { signal?: AbortSignal } = {},
): Promise<AssetHealthResponse> {
  const { data } = await apiClient.get<AssetHealthResponse>(
    `/api/assets/${encodeURIComponent(assetId)}/health`,
    { params: range ? { range } : undefined, signal: config.signal },
  );
  return data;
}
