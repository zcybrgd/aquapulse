import { mapAgentAuditRunDetail } from "../lib/agentAudit";
import type {
  AgentAuditEventDetail,
  AgentAuditFilters,
  AgentAuditRunDetail,
  AgentAuditRunListResponse,
  AgentAuditSummary,
} from "../types/agentAudit";
import { apiClient } from "./client";

function toQuery(filters: AgentAuditFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.agent_code.trim()) query.agent_code = filters.agent_code.trim();
  if (filters.status.trim()) query.status = filters.status.trim();
  if (filters.decision.trim()) query.decision = filters.decision.trim();
  if (filters.incident.trim()) query.incident = filters.incident.trim();
  if (filters.detection.trim()) query.detection = filters.detection.trim();
  if (filters.device.trim()) query.device = filters.device.trim();
  if (filters.search.trim()) query.search = filters.search.trim();
  return query;
}

export async function fetchAgentAuditSummary(
  filters: AgentAuditFilters,
  options?: { signal?: AbortSignal },
): Promise<AgentAuditSummary> {
  const { data } = await apiClient.get<AgentAuditSummary>("/api/agent-audit/summary", {
    params: toQuery(filters),
    signal: options?.signal,
  });
  return data;
}

export async function fetchAgentAuditRuns(
  filters: AgentAuditFilters,
  options?: { signal?: AbortSignal },
): Promise<AgentAuditRunListResponse> {
  const { data } = await apiClient.get<AgentAuditRunListResponse>("/api/agent-audit/runs", {
    params: { ...toQuery(filters), page_size: "50" },
    signal: options?.signal,
  });
  return data;
}

export async function fetchAgentAuditRun(
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<AgentAuditRunDetail> {
  const { data } = await apiClient.get<unknown>(`/api/agent-audit/runs/${encodeURIComponent(runId)}`, {
    signal: options?.signal,
  });
  return mapAgentAuditRunDetail(data);
}

export async function fetchAgentAuditEvent(eventId: string): Promise<AgentAuditEventDetail> {
  const { data } = await apiClient.get<AgentAuditEventDetail>(
    `/api/agent-audit/events/${encodeURIComponent(eventId)}`,
  );
  return data;
}
