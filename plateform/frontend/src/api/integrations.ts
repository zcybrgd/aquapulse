import { apiClient } from "./client";
import type {
  AgentFindingRecord,
  AgentReadiness,
  AgentRecommendationRecord,
  AgentRunDetail,
  IntegrationBundle,
} from "../types/integrations";

export async function fetchAgentReadiness(options?: { signal?: AbortSignal }): Promise<AgentReadiness> {
  const { data } = await apiClient.get<AgentReadiness>("/api/integrations/agents/readiness", {
    signal: options?.signal,
  });
  return data;
}

export async function fetchAgentFindings(options?: { signal?: AbortSignal }): Promise<AgentFindingRecord[]> {
  const { data } = await apiClient.get<AgentFindingRecord[]>("/api/integrations/agents/findings", {
    signal: options?.signal,
  });
  return data;
}

export async function fetchAgentRecommendations(options?: {
  signal?: AbortSignal;
}): Promise<AgentRecommendationRecord[]> {
  const { data } = await apiClient.get<AgentRecommendationRecord[]>("/api/integrations/agents/recommendations", {
    signal: options?.signal,
  });
  return data;
}

const MOCK_MODE = "mock_agent_data";

export async function fetchIntegrationBundle(options?: { signal?: AbortSignal }): Promise<IntegrationBundle> {
  const config = { signal: options?.signal };
  const [readiness, findings, recommendations] = await Promise.all([
    fetchAgentReadiness(config),
    fetchAgentFindings(config),
    fetchAgentRecommendations(config),
  ]);
  return {
    readiness,
    findings: findings.filter((item) => item.data_mode !== MOCK_MODE),
    recommendations: recommendations.filter((item) => item.data_mode !== MOCK_MODE),
  };
}

export async function fetchAgentRun(runId: string, options?: { signal?: AbortSignal }): Promise<AgentRunDetail> {
  const { data } = await apiClient.get<AgentRunDetail>(`/api/integrations/agents/runs/${runId}`, {
    signal: options?.signal,
  });
  return data;
}

export async function fetchAgentFinding(
  findingId: string,
  options?: { signal?: AbortSignal },
): Promise<AgentFindingRecord> {
  const { data } = await apiClient.get<AgentFindingRecord>(`/api/integrations/agents/findings/${findingId}`, {
    signal: options?.signal,
  });
  return data;
}

export async function fetchAgentRecommendation(
  recommendationId: string,
  options?: { signal?: AbortSignal },
): Promise<AgentRecommendationRecord> {
  const { data } = await apiClient.get<AgentRecommendationRecord>(
    `/api/integrations/agents/recommendations/${recommendationId}`,
    { signal: options?.signal },
  );
  return data;
}
