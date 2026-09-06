import { apiClient } from "./client";
import type {
  AddNotePayload,
  DetectionDetail,
  DetectionEvidenceItem,
  DetectionFilters,
  DetectionListResponse,
  DetectionQueueStats,
  DismissPayload,
  InvestigationAgentInputV1,
  InvestigationHistoryResponse,
  MergePayload,
  PromotePayload,
  PromoteResponse,
  ReopenPayload,
  StartReviewPayload,
} from "../types/detections";

export function toDetectionQuery(filters: DetectionFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.search.trim()) query.search = filters.search.trim();
  if (filters.status) query.status = filters.status;
  if (filters.priority) query.priority = filters.priority;
  if (filters.rule) query.rule = filters.rule;
  if (filters.zone) query.zone = filters.zone;
  if (filters.sensor) query.sensor = filters.sensor;
  if (filters.start) {
    const parsed = new Date(filters.start);
    if (!Number.isNaN(parsed.getTime())) query.start = parsed.toISOString();
  }
  if (filters.end) {
    const parsed = new Date(filters.end);
    if (!Number.isNaN(parsed.getTime())) query.end = parsed.toISOString();
  }
  if (filters.sort_by) query.sort_by = filters.sort_by;
  if (filters.sort_order) query.sort_order = filters.sort_order;
  return query;
}

export async function fetchDetections(filters: DetectionFilters): Promise<DetectionListResponse> {
  const { data } = await apiClient.get<DetectionListResponse>("/api/detections", {
    params: toDetectionQuery(filters),
  });
  return data;
}

export async function fetchDetectionSummary(): Promise<DetectionQueueStats> {
  const { data } = await apiClient.get<DetectionQueueStats>("/api/detections/summary");
  return data;
}

export async function fetchDetection(detectionId: string): Promise<DetectionDetail> {
  const { data } = await apiClient.get<DetectionDetail>(
    `/api/detections/${encodeURIComponent(detectionId)}`,
  );
  return data;
}

export async function fetchDetectionEvidence(
  detectionId: string,
): Promise<{ detection_id: string; items: DetectionEvidenceItem[]; data_mode: string }> {
  const { data } = await apiClient.get(`/api/detections/${encodeURIComponent(detectionId)}/evidence`);
  return data;
}

export async function fetchDetectionAgentInput(
  detectionId: string,
): Promise<InvestigationAgentInputV1> {
  const { data } = await apiClient.get<InvestigationAgentInputV1>(
    `/api/detections/${encodeURIComponent(detectionId)}/agent-input`,
  );
  return data;
}

export async function fetchDetectionHistory(detectionId: string): Promise<InvestigationHistoryResponse> {
  const { data } = await apiClient.get<InvestigationHistoryResponse>(
    `/api/detections/${encodeURIComponent(detectionId)}/history`,
  );
  return data;
}

export async function startDetectionReview(
  detectionId: string,
  payload: StartReviewPayload,
): Promise<DetectionDetail> {
  const { data } = await apiClient.post<DetectionDetail>(
    `/api/detections/${encodeURIComponent(detectionId)}/review`,
    payload,
  );
  return data;
}

export async function addDetectionNote(detectionId: string, payload: AddNotePayload): Promise<DetectionDetail> {
  const { data } = await apiClient.post<DetectionDetail>(
    `/api/detections/${encodeURIComponent(detectionId)}/notes`,
    payload,
  );
  return data;
}

export async function dismissDetection(detectionId: string, payload: DismissPayload): Promise<DetectionDetail> {
  const { data } = await apiClient.post<DetectionDetail>(
    `/api/detections/${encodeURIComponent(detectionId)}/dismiss`,
    payload,
  );
  return data;
}

export async function reopenDetection(detectionId: string, payload: ReopenPayload): Promise<DetectionDetail> {
  const { data } = await apiClient.post<DetectionDetail>(
    `/api/detections/${encodeURIComponent(detectionId)}/reopen`,
    payload,
  );
  return data;
}

export async function mergeDetection(detectionId: string, payload: MergePayload): Promise<DetectionDetail> {
  const { data } = await apiClient.post<DetectionDetail>(
    `/api/detections/${encodeURIComponent(detectionId)}/merge`,
    payload,
  );
  return data;
}

export async function promoteDetection(
  detectionId: string,
  payload: PromotePayload,
): Promise<PromoteResponse> {
  const { data } = await apiClient.post<PromoteResponse>(
    `/api/detections/${encodeURIComponent(detectionId)}/promote`,
    payload,
  );
  return data;
}
