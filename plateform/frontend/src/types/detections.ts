export type DetectionStatus =
  | "new"
  | "queued"
  | "under_review"
  | "dismissed"
  | "promoted"
  | "merged";

export type DetectionPriority = "low" | "medium" | "high" | "critical";

export type DetectionSortField = "detected_at" | "priority" | "score" | "status";

export type SortOrder = "asc" | "desc";

export interface DetectionFilters {
  search: string;
  status: DetectionStatus | "";
  priority: DetectionPriority | "";
  rule: string;
  zone: string;
  sensor: string;
  start: string;
  end: string;
  sort_by: DetectionSortField;
  sort_order: SortOrder;
}

export interface DetectionSummary {
  id: string;
  detection_number: string;
  status: DetectionStatus;
  priority: DetectionPriority;
  anomaly_score: number;
  trigger_reason: string;
  reason_codes: string[];
  rule_code: string;
  rule_name: string;
  rule_version: number;
  sensor_id: string;
  sensor_name: string;
  zone: string;
  pipeline_segment: string | null;
  detected_at: string;
  window_start: string;
  window_end: string;
  data_mode: string;
  incident_id: string | null;
  reviewed_by: string | null;
  review_started_at: string | null;
  dismissed_at: string | null;
  dismissal_reason: string | null;
  merged_into_detection_id: string | null;
  resolved_at: string | null;
  updated_at: string | null;
  allowed_actions: string[];
  screening_priority_label: string;
  awaiting_agent_investigation: boolean;
  has_agent_finding: boolean;
}

export interface DetectionEvidenceItem {
  metric: string;
  observed_value: number;
  baseline_value: number | null;
  threshold_value: number | null;
  unit: string;
  evidence_type: string;
  reading_start_time: string;
  reading_end_time: string;
  details: Record<string, unknown>;
}

export interface DetectionDetail extends DetectionSummary {
  asset_status: string;
  pipeline_segment_id: string | null;
  criticality: number | null;
  population_served: number | null;
  reading_count: number;
  correlation_key: string;
  score_explanation: {
    weights?: Record<string, number>;
    factors?: Record<string, number>;
    weighted?: Record<string, number>;
    anomaly_score?: number;
  };
  evidence_summary: Record<string, unknown>;
  evidence: DetectionEvidenceItem[];
  related_detections: DetectionSummary[];
  telemetry_freshness: string | null;
  latest_reading_at: string | null;
  agent_finding: {
    classification: string;
    severity_tier: number;
    confidence_score: number;
    anomaly_score?: number | null;
    operator_justification: string | null;
    mapping_status: string;
    run_id: string | null;
    external_cluster_id: string | null;
  } | null;
}

export interface DetectionListResponse {
  items: DetectionSummary[];
  total: number;
  data_mode: string;
}

export interface DetectionQueueStats {
  new: number;
  queued: number;
  under_review: number;
  high_priority: number;
  critical_priority: number;
  total: number;
  last_run_at: string | null;
  last_run_deduplicated: number | null;
  highest_priority: DetectionSummary | null;
  data_mode: string;
}

export interface InvestigationAgentInputV1 {
  schema_version: "1";
  detection_id: string;
  detected_at: string;
  telemetry_window: { start: string; end: string };
  recent_readings_reference: Record<string, unknown>;
  sensor: {
    id: string;
    name: string;
    operational_status: string;
    manufacturer: string | null;
    model: string | null;
  };
  network_metadata: {
    zone: string;
    signal_strength_dbm: number | null;
    packet_loss_pct: number | null;
    telemetry_freshness: string | null;
    latest_reading_at: string | null;
  };
  rule_triggers: Array<{
    rule_code: string;
    rule_name: string;
    rule_version: number;
    reason_codes: string[];
    trigger_reason: string;
    threshold: number | null;
    secondary_threshold: number | null;
  }>;
  structured_evidence: DetectionEvidenceItem[];
  pipeline_context: {
    segment_id: string | null;
    segment_name: string | null;
    criticality: number | null;
    population_served: number | null;
  };
  criticality: number | null;
  population_served: number | null;
  current_asset_status: string;
  data_mode: string;
  agent_executed: false;
  note: string;
}

export type DismissalReason =
  | "false_positive"
  | "sensor_fault"
  | "planned_operation"
  | "duplicate"
  | "insufficient_evidence"
  | "other";

export type InvestigationEventType =
  | "review_started"
  | "note_added"
  | "dismissed"
  | "reopened"
  | "merged"
  | "promoted";

export type DetectionAction = "start_review" | "add_note" | "dismiss" | "merge" | "promote" | "reopen";

export interface InvestigationEventItem {
  id: string;
  event_type: InvestigationEventType;
  from_status: DetectionStatus | null;
  to_status: DetectionStatus | null;
  actor_name: string;
  note: string | null;
  reason_code: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  target_detection_id: string | null;
  incident_id: string | null;
}

export interface InvestigationHistoryResponse {
  detection_id: string;
  events: InvestigationEventItem[];
}

export interface ActorPayload {
  actor_name: string;
}

export interface StartReviewPayload extends ActorPayload {
  note?: string;
}

export interface AddNotePayload extends ActorPayload {
  note: string;
}

export interface DismissPayload extends ActorPayload {
  reason_code: DismissalReason;
  note?: string;
}

export interface ReopenPayload extends ActorPayload {
  note?: string;
}

export interface MergePayload extends ActorPayload {
  target_detection_id: string;
  note?: string;
}

export interface PromotePayload extends ActorPayload {
  title: string;
  severity: "tier_1" | "tier_2" | "tier_3";
  classification:
    | "confirmed_leak"
    | "suspected_leak"
    | "connectivity_degradation"
    | "sensor_fault"
    | "pressure_anomaly"
    | "normal_demand_spike"
    | "insufficient_data";
  summary: string;
  note?: string;
}

export interface PromoteResponse {
  detection: DetectionDetail;
  incident: {
    id: string;
    incident_number: string;
    title: string;
    classification: PromotePayload["classification"];
    severity: PromotePayload["severity"];
    status: string;
  };
}

export interface ApiErrorDetail {
  message: string;
  code?: string;
  incident_id?: string;
  target_detection_id?: string;
}
