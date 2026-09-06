export interface AgentAuditFilters {
  agent_code: string;
  status: string;
  decision: string;
  incident: string;
  detection: string;
  device: string;
  search: string;
}

export interface AgentCount {
  key: string;
  count: number;
}

export interface AgentAuditSummary {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  blocked_actions: number;
  average_duration_ms: number | null;
  runs_by_agent: AgentCount[];
  stages_reached: AgentCount[];
  last_run_at: string | null;
  unmapped_identity_count: number;
  data_mode: string;
  reference_time: string;
  note: string;
}

export interface AgentAuditEventSummary {
  id: string;
  public_id: string;
  agent_run_id: string | null;
  agent_code: string;
  contract_version: string;
  pipeline_stage: string;
  node_name: string | null;
  sequence_number: number;
  event_type: string;
  status: string;
  summary: string;
  incident_public_id: string | null;
  detection_public_id: string | null;
  asset_public_id: string | null;
  external_cluster_id: string | null;
  external_device_id: string | null;
  error_code: string | null;
  error_message: string | null;
  duration_ms: number | null;
  data_mode: string;
  occurred_at: string;
  reasoning_summary: string | null;
}

export interface AgentAuditEventDetail extends AgentAuditEventSummary {
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  reasoning_trace: unknown;
  safety_checks: unknown;
}

export interface LinkedFinding {
  classification: string;
  severity_tier: number;
  confidence_score: number;
  operator_justification: string | null;
  mapping_status: string;
  external_cluster_id: string | null;
  mapped_detection_id: string | null;
}

export interface AgentAuditRunSummary {
  id: string;
  public_id: string;
  agent_code: string;
  agent_type: string;
  contract_version: string;
  pipeline_stages: string[];
  source_type: string;
  source_public_id: string | null;
  status: string;
  classification: string | null;
  investigation_severity: number | null;
  decision: string | null;
  duration_ms: number | null;
  started_at: string;
  related_incident: string | null;
  related_detection: string | null;
  related_device: string | null;
  external_cluster_id: string | null;
  data_mode: string;
  blocked: boolean;
  contract_unconfirmed: boolean;
  mapping_status: string | null;
}

export interface AgentAuditRunDetail extends AgentAuditRunSummary {
  events: AgentAuditEventDetail[];
  findings: LinkedFinding[];
  recommendation_decisions: string[];
  valve_command_sent: boolean;
  valve_command_confirmed: boolean;
  notification_sent: boolean;
  safety_status: string | null;
  note: string;
}

export interface AgentAuditRunListResponse {
  items: AgentAuditRunSummary[];
  total: number;
  page: number;
  page_size: number;
  data_mode: string;
  reference_time: string;
}
