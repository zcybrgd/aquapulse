import { apiClient } from "./client";
import type {
  IncidentDetail,
  IncidentFilters,
  IncidentListResponse,
  IncidentTimelineResponse,
} from "../types/incidents";

export function toIncidentQuery(filters: IncidentFilters): Record<string, string> {
  const query: Record<string, string> = {};

  if (filters.search.trim()) {
    query.search = filters.search.trim();
  }
  if (filters.severity) {
    query.severity = filters.severity;
  }
  if (filters.status) {
    query.status = filters.status;
  }
  if (filters.classification) {
    query.classification = filters.classification;
  }
  if (filters.zone) {
    query.zone = filters.zone;
  }
  if (filters.sort_by) {
    query.sort_by = filters.sort_by;
  }
  if (filters.sort_order) {
    query.sort_order = filters.sort_order;
  }

  return query;
}

export async function fetchIncidents(
  filters: IncidentFilters,
): Promise<IncidentListResponse> {
  const { data } = await apiClient.get<IncidentListResponse>("/api/incidents", {
    params: toIncidentQuery(filters),
  });
  return data;
}

export async function fetchIncident(incidentId: string): Promise<IncidentDetail> {
  const { data } = await apiClient.get<IncidentDetail>(
    `/api/incidents/${encodeURIComponent(incidentId)}`,
  );
  return data;
}

export async function fetchIncidentTimeline(
  incidentId: string,
): Promise<IncidentTimelineResponse> {
  const { data } = await apiClient.get<IncidentTimelineResponse>(
    `/api/incidents/${encodeURIComponent(incidentId)}/timeline`,
  );
  return data;
}
