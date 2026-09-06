export type SeverityTier = "tier_1" | "tier_2" | "tier_3";

export type IncidentClassification =
  | "confirmed_leak"
  | "suspected_leak"
  | "connectivity_degradation"
  | "sensor_fault"
  | "pressure_anomaly"
  | "normal_demand_spike"
  | "insufficient_data";

export type IncidentStatus =
  | "open"
  | "acknowledged"
  | "investigating"
  | "awaiting_approval"
  | "responding"
  | "monitoring"
  | "resolved"
  | "false_alarm";

export type ResolutionCode =
  | "leak_repaired"
  | "isolated_for_maintenance"
  | "sensor_fault"
  | "planned_operation"
  | "false_alarm"
  | "monitoring_completed"
  | "other";

export type ResponseTaskStatus = "todo" | "in_progress" | "completed" | "cancelled";
export type ResponseTaskPriority = "low" | "medium" | "high" | "critical";

export type TimelineSource = "detector" | "agent" | "network" | "operator" | "system";

export type IncidentSortField =
  | "detected_at"
  | "severity"
  | "status"
  | "estimated_loss"
  | "priority";

export type SortOrder = "asc" | "desc";

export interface IncidentFilters {
  search: string;
  severity: SeverityTier | "";
  status: IncidentStatus | "";
  classification: IncidentClassification | "";
  zone: string;
  sort_by: IncidentSortField;
  sort_order: SortOrder;
}

export interface IncidentSummary {
  id: string;
  incident_number: string;
  title: string;
  classification: IncidentClassification;
  severity: SeverityTier;
  status: IncidentStatus;
  zone: string;
  pipeline_segment: string;
  location: string;
  detected_at: string;
  updated_at: string;
  estimated_water_loss_m3: number;
  assigned_operator: string | null;
}

export interface EvidenceItem {
  id: string;
  kind: string;
  title: string;
  detail: string;
}

export interface IncidentTelemetryPoint {
  timestamp: string;
  pressure: number;
  flow_rate: number;
  packet_loss: number;
  is_detection: boolean;
}

export interface IncidentDetail extends IncidentSummary {
  confidence: number;
  sensor: string;
  associated_valve: string;
  latitude: number;
  longitude: number;
  population_affected: number;
  current_summary: string;
  pressure_change_bar: number;
  flow_change_m3h: number;
  network_condition: string;
  signal_strength_dbm: number;
  packet_loss_percent: number;
  device_reachability: string;
  network_priority_status: string;
  agent_investigation_summary: string;
  recommended_action: string;
  evidence: EvidenceItem[];
  telemetry: IncidentTelemetryPoint[];
}

export interface IncidentListResponse {
  items: IncidentSummary[];
  total: number;
}

export interface IncidentTimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  source: TimelineSource;
  status: string;
  actor_name?: string | null;
  response_task_id?: string | null;
}

export interface IncidentTimelineResponse {
  incident_id: string;
  events: IncidentTimelineEvent[];
}

export interface IncidentCenterStats {
  total: number;
  critical: number;
  awaitingApproval: number;
  investigating: number;
  resolvedToday: number;
  active: number;
}

export interface ResponseTaskItem {
  id: string;
  public_id: string;
  incident_id: string;
  title: string;
  description: string | null;
  status: ResponseTaskStatus;
  priority: ResponseTaskPriority;
  assigned_to: string | null;
  created_by: string;
  due_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  completed_by: string | null;
  completion_note: string | null;
  created_at: string;
  updated_at: string;
  overdue: boolean;
}

export interface IncidentOperations {
  incident_id: string;
  status: IncidentStatus;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  assigned_to: string | null;
  response_started_at: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_code: ResolutionCode | null;
  resolution_summary: string | null;
  allowed_actions: string[];
  incomplete_task_count: number;
  tasks: ResponseTaskItem[];
}

export interface OperationsSummary {
  active_incidents: number;
  unacknowledged: number;
  acknowledged: number;
  investigating: number;
  awaiting_approval: number;
  responding: number;
  overdue_tasks: number;
  critical_active: number;
}

export interface OperationsQueueItem extends IncidentSummary {
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  assigned_to: string | null;
  response_started_at: string | null;
  allowed_actions: string[];
  open_task_count: number;
  overdue_task_count: number;
  completed_task_count: number;
  latest_update: string | null;
  latest_update_at: string | null;
}

export interface OperationsQueueResponse {
  items: OperationsQueueItem[];
  total: number;
  summary: OperationsSummary;
  overdue_tasks: ResponseTaskItem[];
  upcoming_tasks: ResponseTaskItem[];
}

export interface OperationsFilters {
  search: string;
  severity: SeverityTier | "";
  status: IncidentStatus | "";
  zone: string;
  assigned_to: string;
}
