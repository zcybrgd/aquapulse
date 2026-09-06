import { apiClient } from "./client";
import type {
  NetworkEventDetail,
  NetworkEventListResponse,
  NetworkFilters,
  NetworkSummary,
} from "../types/networkHealth";

function toIsoQuery(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? trimmed : parsed.toISOString();
}

function toQuery(filters: NetworkFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.event_type.trim()) query.event_type = filters.event_type.trim();
  if (filters.status.trim()) query.status = filters.status.trim();
  if (filters.device.trim()) query.device = filters.device.trim();
  if (filters.cluster.trim()) query.cluster = filters.cluster.trim();
  if (filters.incident.trim()) query.incident = filters.incident.trim();
  if (filters.search.trim()) query.search = filters.search.trim();
  const start = toIsoQuery(filters.start);
  const end = toIsoQuery(filters.end);
  if (start) query.start = start;
  if (end) query.end = end;
  return query;
}

export async function fetchNetworkSummary(
  filters: NetworkFilters,
  options?: { signal?: AbortSignal },
): Promise<NetworkSummary> {
  const { data } = await apiClient.get<NetworkSummary>("/api/network-health/summary", {
    params: toQuery(filters),
    signal: options?.signal,
  });
  return data;
}

export async function fetchNetworkEvents(
  filters: NetworkFilters,
  options?: { signal?: AbortSignal },
): Promise<NetworkEventListResponse> {
  const { data } = await apiClient.get<NetworkEventListResponse>("/api/network-health/events", {
    params: { ...toQuery(filters), page_size: "50" },
    signal: options?.signal,
  });
  return data;
}

export async function fetchNetworkEvent(eventId: string): Promise<NetworkEventDetail> {
  const { data } = await apiClient.get<NetworkEventDetail>(
    `/api/network-health/events/${encodeURIComponent(eventId)}`,
  );
  return data;
}
