export interface SafetyFlags {
  camara_enabled: boolean;
  notifications_enabled: boolean;
  physical_commands_enabled: boolean;
  agent_execution_enabled: boolean;
  result_ingest_enabled: boolean;
}

export interface AgentSummary {
  agent_code: string;
  display_name: string;
  enabled: boolean;
  mode: string;
  contract_version: string;
  url_configured: boolean;
  health_status: string;
  last_health_check_at: string | null;
  reachable: boolean;
}

export interface MappingCoverage {
  enabled_mappings: number;
  unmapped_findings: number;
}

export interface AgentRunSummary {
  run_id: string;
  agent_type: string;
  status: string;
  source_type: string;
  source_public_id: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  data_mode: string;
  mapping_warning_count: number;
  error_code: string | null;
}

export interface AgentReadiness {
  prepared: boolean;
  execution_enabled: boolean;
  banner: string;
  advisory_notice: string;
  actuation_notice: string;
  safety: SafetyFlags;
  agents: AgentSummary[];
  mapping_coverage: MappingCoverage;
  last_runs: AgentRunSummary[];
  contract_docs: Record<string, string>;
}

export interface AgentRunDetail extends AgentRunSummary {
  correlation_id: string;
  idempotency_key: string;
  contract_version: string;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown> | null;
  validation_errors: unknown[];
  mapping_warnings: unknown[];
  error_message: string | null;
}

export interface AgentFindingRecord {
  id: string;
  run_id: string;
  provider: string;
  external_anomaly_id: string;
  classification: string;
  classification_label: string;
  severity_tier: number;
  severity_label: string;
  confidence_score: number;
  external_cluster_id: string | null;
  external_segment_id: string | null;
  external_valve_id: string | null;
  mapped_detection_id: string | null;
  mapped_sensor_id: string | null;
  mapped_segment_id: string | null;
  mapped_valve_id: string | null;
  mapping_status: string;
  review_status: string;
  network_status: Record<string, unknown>;
  physical_deviations: Record<string, unknown>;
  criticality_metrics: Record<string, unknown>;
  operator_justification: string | null;
  advisory: boolean;
  data_mode?: string;
  created_at: string;
}

export interface AgentRecommendationRecord {
  id: string;
  run_id: string;
  provider: string;
  external_result_id: string;
  external_incident_id: string | null;
  external_cluster_id: string | null;
  external_device_id: string | null;
  mapped_incident_number: string | null;
  mapped_device_id: string | null;
  incident_attached: boolean;
  severity_tier: number;
  severity_label: string;
  decision: string;
  reachability: Record<string, unknown>;
  notification_sent: boolean;
  notification_verified: boolean;
  valve_command_sent: boolean;
  valve_command_confirmed: boolean;
  valve_command_verified: boolean;
  human_override_requested: boolean;
  human_override_response: string | null;
  reasoning_trace: unknown;
  safety_status: string;
  advisory: boolean;
  data_mode?: string;
  created_at: string;
}

export interface IntegrationBundle {
  readiness: AgentReadiness;
  findings: AgentFindingRecord[];
  recommendations: AgentRecommendationRecord[];
}

export type AgentHealthStatus = "not_configured" | "checking" | "healthy" | "unavailable";
export type AgentContractStatus = "unknown" | "compatible" | "incompatible" | "unavailable";
export type AgentRuntimeType = "investigation_agent" | "network_management_agent" | "response_agent";
export type AgentStatusErrorCode =
  | "agent_not_configured"
  | "agent_unreachable"
  | "agent_health_timeout"
  | "agent_health_invalid"
  | "agent_contract_unavailable"
  | "agent_contract_mismatch";

export interface AgentRuntimeStatus {
  agent_type: AgentRuntimeType;
  display_name: string;
  configured: boolean;
  execution_enabled: boolean;
  reachable: boolean;
  health_status: AgentHealthStatus;
  contract_status: AgentContractStatus;
  contract_version: string | null;
  checked_at: string;
  response_time_ms: number | null;
  error_code: AgentStatusErrorCode | null;
  error_message: string | null;
}

export interface IntegrationStatus {
  generated_at: string;
  execution_globally_enabled: boolean;
  agents: AgentRuntimeStatus[];
}
