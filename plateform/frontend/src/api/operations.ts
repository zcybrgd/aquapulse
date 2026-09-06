import { apiClient } from "./client";
import type {
  IncidentOperations,
  OperationsFilters,
  OperationsQueueResponse,
  ResolutionCode,
  ResponseTaskItem,
  ResponseTaskPriority,
} from "../types/incidents";

export function toOperationsQuery(filters: OperationsFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.search.trim()) query.search = filters.search.trim();
  if (filters.severity) query.severity = filters.severity;
  if (filters.status) query.status = filters.status;
  if (filters.zone) query.zone = filters.zone;
  if (filters.assigned_to.trim()) query.assigned_to = filters.assigned_to.trim();
  return query;
}

export async function fetchOperationsQueue(filters: OperationsFilters): Promise<OperationsQueueResponse> {
  const { data } = await apiClient.get<OperationsQueueResponse>("/api/operations/queue", {
    params: toOperationsQuery(filters),
  });
  return data;
}

export async function fetchIncidentOperations(incidentId: string): Promise<IncidentOperations> {
  const { data } = await apiClient.get<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/operations`,
  );
  return data;
}

export async function acknowledgeIncident(incidentId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/acknowledge`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function assignIncident(incidentId: string, actorName: string, assignedTo: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/assign`,
    { actor_name: actorName, assigned_to: assignedTo, note },
  );
  return data;
}

export async function startIncidentInvestigation(incidentId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/start-investigation`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function requestIncidentApproval(incidentId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/request-approval`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function startIncidentResponse(incidentId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/start-response`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function addIncidentNote(incidentId: string, actorName: string, note: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/notes`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function resolveIncident(
  incidentId: string,
  actorName: string,
  resolutionCode: ResolutionCode,
  resolutionSummary: string,
  confirmIncompleteTasks = false,
) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/resolve`,
    {
      actor_name: actorName,
      resolution_code: resolutionCode,
      resolution_summary: resolutionSummary,
      confirm_incomplete_tasks: confirmIncompleteTasks,
    },
  );
  return data;
}

export async function markIncidentFalseAlarm(incidentId: string, actorName: string, summary: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/false-alarm`,
    { actor_name: actorName, resolution_summary: summary, note },
  );
  return data;
}

export async function reopenIncident(incidentId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<IncidentOperations>(
    `/api/incidents/${encodeURIComponent(incidentId)}/reopen`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function createResponseTask(
  incidentId: string,
  actorName: string,
  payload: { title: string; description?: string; priority: ResponseTaskPriority; assigned_to?: string; due_at?: string },
) {
  const { data } = await apiClient.post<ResponseTaskItem>(
    `/api/incidents/${encodeURIComponent(incidentId)}/tasks`,
    { actor_name: actorName, ...payload },
  );
  return data;
}

export async function startResponseTask(incidentId: string, taskId: string, actorName: string) {
  const { data } = await apiClient.post<ResponseTaskItem>(
    `/api/incidents/${encodeURIComponent(incidentId)}/tasks/${encodeURIComponent(taskId)}/start`,
    { actor_name: actorName },
  );
  return data;
}

export async function completeResponseTask(incidentId: string, taskId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<ResponseTaskItem>(
    `/api/incidents/${encodeURIComponent(incidentId)}/tasks/${encodeURIComponent(taskId)}/complete`,
    { actor_name: actorName, completion_note: note },
  );
  return data;
}

export async function cancelResponseTask(incidentId: string, taskId: string, actorName: string, note?: string) {
  const { data } = await apiClient.post<ResponseTaskItem>(
    `/api/incidents/${encodeURIComponent(incidentId)}/tasks/${encodeURIComponent(taskId)}/cancel`,
    { actor_name: actorName, note },
  );
  return data;
}
