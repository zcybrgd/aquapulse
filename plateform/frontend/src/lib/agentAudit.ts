import type {
  AgentAuditEventDetail,
  AgentAuditRunDetail,
  AgentAuditRunStatus,
  JsonObject,
  JsonValue,
  LinkedFinding,
} from "../types/agentAudit";

export const ACTIVE_AGENT_RUN_STATUSES: readonly AgentAuditRunStatus[] = [
  "pending",
  "validating",
  "ready",
  "running",
];

export const AGENT_CODE_LABELS: Record<string, string> = {
  investigation_agent: "Investigation Agent",
  response_agent: "Response Agent",
  network_management_agent: "Network Agent",
};

export const STAGE_LABELS: Record<string, string> = {
  lightweight_detection: "Screening result",
  anomaly_investigation: "Investigation Agent",
  network_management: "Network Agent",
  response: "Response Agent",
  platform_safety: "Platform safety decision",
  audit: "Audit",
};

const HIDDEN_REASONING_KEYS = new Set([
  "reasoning_trace",
  "reasoning",
  "reasoning_summary",
  "chain_of_thought",
  "hidden_reasoning",
  "cot",
  "thoughts",
  "internal_thoughts",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNullableString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function asJsonValue(value: unknown): JsonValue {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(asJsonValue);
  }
  if (isRecord(value)) {
    const mapped: JsonObject = {};
    for (const [key, item] of Object.entries(value)) {
      mapped[key] = asJsonValue(item);
    }
    return mapped;
  }
  return null;
}

function asJsonObject(value: unknown): JsonObject {
  const mapped = asJsonValue(value);
  if (mapped !== null && typeof mapped === "object" && !Array.isArray(mapped)) {
    return mapped;
  }
  return {};
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

export function isActiveAgentRunStatus(status: string): boolean {
  return (ACTIVE_AGENT_RUN_STATUSES as readonly string[]).includes(status);
}

export function agentCodeLabel(agentCode: string): string {
  return AGENT_CODE_LABELS[agentCode] ?? agentCode;
}

export function stageLabel(pipelineStage: string): string {
  return STAGE_LABELS[pipelineStage] ?? pipelineStage;
}

export function eventTypeLabel(event: Pick<AgentAuditEventDetail, "pipeline_stage" | "event_type" | "node_name">): string {
  if (event.node_name && event.node_name.trim()) {
    return event.node_name;
  }
  return event.event_type;
}

export function omitHiddenReasoning(value: JsonValue): JsonValue {
  if (Array.isArray(value)) {
    return value.map(omitHiddenReasoning);
  }
  if (value !== null && typeof value === "object") {
    const cleaned: JsonObject = {};
    for (const [key, item] of Object.entries(value)) {
      if (HIDDEN_REASONING_KEYS.has(key)) continue;
      cleaned[key] = omitHiddenReasoning(item);
    }
    return cleaned;
  }
  return value;
}

function eventTimestampMs(occurredAt: string): number {
  const parsed = Date.parse(occurredAt);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function sortAuditEventsChronologically(events: AgentAuditEventDetail[]): AgentAuditEventDetail[] {
  return [...events].sort((left, right) => {
    const byTime = eventTimestampMs(left.occurred_at) - eventTimestampMs(right.occurred_at);
    if (byTime !== 0) return byTime;
    return left.sequence_number - right.sequence_number;
  });
}

export function auditTimelineHeading(
  run: Pick<AgentAuditRunDetail, "status" | "events"> & { started_at?: string | null },
): string {
  if (run.events.length > 0) {
    if (isActiveAgentRunStatus(run.status)) {
      return "Partial audit timeline";
    }
    return "Chronological stage timeline";
  }
  if (run.started_at) {
    return "Run timeline";
  }
  return "No audit events recorded";
}

function mapAuditEvent(value: unknown): AgentAuditEventDetail | null {
  if (!isRecord(value)) return null;
  const id = asString(value.id);
  const publicId = asString(value.public_id);
  const agentCode = asString(value.agent_code);
  const contractVersion = asString(value.contract_version);
  const pipelineStage = asString(value.pipeline_stage);
  const eventType = asString(value.event_type);
  const status = asString(value.status);
  const summary = asString(value.summary);
  const dataMode = asString(value.data_mode);
  const occurredAt = asString(value.occurred_at);
  const sequenceNumber = asNumber(value.sequence_number);
  if (
    id === null ||
    publicId === null ||
    agentCode === null ||
    contractVersion === null ||
    pipelineStage === null ||
    eventType === null ||
    status === null ||
    summary === null ||
    dataMode === null ||
    occurredAt === null ||
    sequenceNumber === null
  ) {
    return null;
  }
  return {
    id,
    public_id: publicId,
    agent_run_id: asNullableString(value.agent_run_id),
    agent_code: agentCode,
    contract_version: contractVersion,
    pipeline_stage: pipelineStage,
    node_name: asNullableString(value.node_name),
    sequence_number: sequenceNumber,
    event_type: eventType,
    status,
    summary,
    incident_public_id: asNullableString(value.incident_public_id),
    detection_public_id: asNullableString(value.detection_public_id),
    asset_public_id: asNullableString(value.asset_public_id),
    external_cluster_id: asNullableString(value.external_cluster_id),
    external_device_id: asNullableString(value.external_device_id),
    error_code: asNullableString(value.error_code),
    error_message: asNullableString(value.error_message),
    duration_ms: asNumber(value.duration_ms),
    data_mode: dataMode,
    occurred_at: occurredAt,
    reasoning_summary: asNullableString(value.reasoning_summary),
    input_summary: asJsonObject(value.input_summary),
    output_summary: asJsonObject(value.output_summary),
    reasoning_trace: asJsonValue(value.reasoning_trace),
    safety_checks: asJsonValue(value.safety_checks),
  };
}

function mapFinding(value: unknown): LinkedFinding | null {
  if (!isRecord(value)) return null;
  const classification = asString(value.classification);
  const severityTier = asNumber(value.severity_tier);
  const confidenceScore = asNumber(value.confidence_score);
  const mappingStatus = asString(value.mapping_status);
  if (classification === null || severityTier === null || confidenceScore === null || mappingStatus === null) {
    return null;
  }
  return {
    classification,
    severity_tier: severityTier,
    confidence_score: confidenceScore,
    operator_justification: asNullableString(value.operator_justification),
    mapping_status: mappingStatus,
    external_cluster_id: asNullableString(value.external_cluster_id),
    mapped_detection_id: asNullableString(value.mapped_detection_id),
  };
}

export function readAuditEvents(payload: unknown): AgentAuditEventDetail[] {
  if (!isRecord(payload) || !Array.isArray(payload.events)) {
    return [];
  }
  return sortAuditEventsChronologically(
    payload.events.map(mapAuditEvent).filter((event): event is AgentAuditEventDetail => event !== null),
  );
}

export function mapAgentAuditRunDetail(payload: unknown): AgentAuditRunDetail {
  if (!isRecord(payload)) {
    throw new Error("Invalid agent audit run response");
  }
  const id = asString(payload.id);
  const publicId = asString(payload.public_id);
  const agentCode = asString(payload.agent_code);
  const agentType = asString(payload.agent_type);
  const contractVersion = asString(payload.contract_version);
  const sourceType = asString(payload.source_type);
  const status = asString(payload.status);
  const startedAt = asString(payload.started_at);
  const dataMode = asString(payload.data_mode);
  const blocked = asBoolean(payload.blocked);
  const contractUnconfirmed = asBoolean(payload.contract_unconfirmed);
  const valveCommandSent = asBoolean(payload.valve_command_sent);
  const valveCommandConfirmed = asBoolean(payload.valve_command_confirmed);
  const notificationSent = asBoolean(payload.notification_sent);
  const note = asString(payload.note);
  if (
    id === null ||
    publicId === null ||
    agentCode === null ||
    agentType === null ||
    contractVersion === null ||
    sourceType === null ||
    status === null ||
    startedAt === null ||
    dataMode === null ||
    blocked === null ||
    contractUnconfirmed === null ||
    valveCommandSent === null ||
    valveCommandConfirmed === null ||
    notificationSent === null ||
    note === null
  ) {
    throw new Error("Invalid agent audit run response");
  }
  return {
    id,
    public_id: publicId,
    agent_code: agentCode,
    agent_type: agentType,
    contract_version: contractVersion,
    pipeline_stages: asStringArray(payload.pipeline_stages),
    source_type: sourceType,
    source_public_id: asNullableString(payload.source_public_id),
    status,
    classification: asNullableString(payload.classification),
    investigation_severity: asNumber(payload.investigation_severity),
    decision: asNullableString(payload.decision),
    duration_ms: asNumber(payload.duration_ms),
    started_at: startedAt,
    related_incident: asNullableString(payload.related_incident),
    related_detection: asNullableString(payload.related_detection),
    related_device: asNullableString(payload.related_device),
    external_cluster_id: asNullableString(payload.external_cluster_id),
    data_mode: dataMode,
    blocked,
    contract_unconfirmed: contractUnconfirmed,
    mapping_status: asNullableString(payload.mapping_status),
    events: readAuditEvents(payload),
    findings: Array.isArray(payload.findings)
      ? payload.findings.map(mapFinding).filter((item): item is LinkedFinding => item !== null)
      : [],
    recommendation_decisions: asStringArray(payload.recommendation_decisions),
    valve_command_sent: valveCommandSent,
    valve_command_confirmed: valveCommandConfirmed,
    notification_sent: notificationSent,
    safety_status: asNullableString(payload.safety_status),
    note,
  };
}
