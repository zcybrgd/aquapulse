import type { AgentAuditEventDetail, AgentAuditRunDetail, JsonObject, JsonValue } from "../types/agentAudit";
import type { AgentFindingRecord, AgentRecommendationRecord, AgentRunDetail } from "../types/integrations";
import { agentCodeLabel, auditTimelineHeading, omitHiddenReasoning } from "./agentAudit";
import { formatDateTime, formatNumber, formatPercent } from "./format";

const UNAVAILABLE = "Unavailable";

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

const SENSITIVE_KEY_TOKENS = [
  "api_key",
  "apikey",
  "token",
  "authorization",
  "secret",
  "password",
  "cookie",
  "operator_contact",
  "device_msisdn",
  "phonenumber",
  "phone_number",
  "msisdn",
  "x-rapidapi-key",
  "rapidapi_key",
  "base_url",
  "service_url",
  "webhook_url",
];

const PATH_RE = /(?:\/home\/|\/Users\/|[A-Za-z]:\\Users\\)/i;
const INTERNAL_URL_RE =
  /https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+|192\.168\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+)\S*/i;
const URL_KEY_RE = /(^|_)url$/i;
const REDACTED = "[REDACTED]";

export const CLASSIFICATION_LABELS: Record<string, string> = {
  confirmed_anomaly: "Agent-assessed anomaly",
  confirmed_instrument_fault: "Agent-assessed instrument fault",
};

export const DECISION_LABELS: Record<string, string> = {
  LOG_ONLY: "Log only",
  ALERT_AND_AWAIT: "Alert and await approval",
  AUTONOMOUS_ISOLATE: "Isolation requested",
  ESCALATE_UNREACHABLE: "Escalate — device unreachable",
};

export const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  validating: "Validating",
  ready: "Ready",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  rejected: "Rejected",
  cancelled: "Cancelled",
  blocked: "Blocked",
  advisory: "Advisory",
  agent_reported_unverified: "Agent-reported, unverified",
  mapped: "Mapped",
  unmapped: "Unmapped",
  partial: "Partial",
};

export const DATA_MODE_LABELS: Record<string, string> = {
  simulated: "Simulated",
  ingested: "Ingested",
  mock_agent_data: "Mock agent data",
};

export const ENTITY_LABELS: Record<string, string> = {
  sensor_cluster: "Sensor cluster",
  segment: "Segment",
  valve: "Associated valve",
  device: "Device",
  detection: "Detection",
  incident: "Incident",
  asset: "Asset",
};

export interface MappingRow {
  entityType: string;
  label: string;
  externalId: string;
  mappedId: string | null;
  mapped: boolean;
  href: string | null;
}

export interface InvestigationBatchView {
  batchId: string | null;
  analysisTimestamp: string | null;
  totalClustersAnalyzed: number | null;
  anomaliesDetected: number | null;
}

export interface InvestigationFindingView {
  key: string;
  anomalyId: string | null;
  classification: string;
  severityTier: number;
  confidence: number | null;
  clusterId: string | null;
  segmentId: string | null;
  valveId: string | null;
  mappingStatus: string;
  mappedDetectionId: string | null;
  mappedSegmentId: string | null;
  mappedValveId: string | null;
  mappedSensorId: string | null;
  justification: string | null;
  physical: Record<string, JsonValue>;
  criticality: Record<string, JsonValue>;
  network: Record<string, JsonValue>;
}

export interface ResponseResultView {
  incidentId: string | null;
  deviceId: string | null;
  clusterId: string | null;
  mappedIncident: string | null;
  mappedDevice: string | null;
  severityTier: number | null;
  reachability: string | null;
  decision: string | null;
  operatorMessage: string | null;
  humanOverrideRequested: boolean | null;
  humanOverrideResponse: string | null;
  notificationSent: boolean;
  valveCommandSent: boolean;
  valveCommandConfirmed: boolean;
  valveCommandVerified: boolean;
  createdAt: string | null;
  safetyStatus: string | null;
  reasoningSteps: string[];
  blockedReason: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function asJsonObject(value: unknown): Record<string, JsonValue> {
  if (!isRecord(value)) return {};
  const mapped: Record<string, JsonValue> = {};
  for (const [key, item] of Object.entries(value)) {
    mapped[key] = item as JsonValue;
  }
  return mapped;
}

function isSensitiveKey(key: string): boolean {
  const lowered = key.toLowerCase();
  return SENSITIVE_KEY_TOKENS.some((token) => lowered.includes(token)) || URL_KEY_RE.test(lowered);
}

function isSensitiveValue(value: string): boolean {
  return PATH_RE.test(value) || INTERNAL_URL_RE.test(value);
}

export function sanitizeDisplayValue(value: unknown): JsonValue {
  if (typeof value === "string") {
    return isSensitiveValue(value) ? REDACTED : value;
  }
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (Array.isArray(value)) return value.map((item) => sanitizeDisplayValue(item));
  if (isRecord(value)) {
    const cleaned: JsonObject = {};
    for (const [key, item] of Object.entries(value)) {
      if (HIDDEN_REASONING_KEYS.has(key) || isSensitiveKey(key)) {
        if (HIDDEN_REASONING_KEYS.has(key)) continue;
        cleaned[key] = REDACTED;
      } else {
        cleaned[key] = sanitizeDisplayValue(item);
      }
    }
    return cleaned;
  }
  return null;
}

export function humanLabel(value: string | null | undefined, table: Record<string, string>): string {
  if (!value) return UNAVAILABLE;
  return table[value] ?? value.replaceAll("_", " ");
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

export function dataModeLabel(mode: string): string {
  return DATA_MODE_LABELS[mode] ?? mode.replaceAll("_", " ");
}

export function classificationLabel(value: string): string {
  return CLASSIFICATION_LABELS[value] ?? value.replaceAll("_", " ");
}

export function decisionLabel(value: string | null): string {
  if (!value) return UNAVAILABLE;
  return DECISION_LABELS[value] ?? value.replaceAll("_", " ");
}

export function formatOptionalNumber(value: unknown, fractionDigits = 1, suffix = ""): string {
  const numeric = asNumber(value);
  if (numeric === null) return UNAVAILABLE;
  return `${formatNumber(numeric, fractionDigits)}${suffix}`;
}

export function formatOptionalPercent(value: unknown): string {
  const numeric = asNumber(value);
  if (numeric === null) return UNAVAILABLE;
  return formatPercent(numeric, 1);
}

export function formatOptionalInteger(value: unknown): string {
  const numeric = asNumber(value);
  if (numeric === null) return UNAVAILABLE;
  return formatNumber(numeric, 0);
}

export function formatOptionalBoolean(value: unknown): string {
  if (typeof value !== "boolean") return UNAVAILABLE;
  return value ? "Yes" : "No";
}

export function formatOptionalText(value: unknown): string {
  const text = asString(value);
  return text ?? UNAVAILABLE;
}

export function formatOptionalTimestamp(value: unknown): string {
  const text = asString(value);
  return text ? formatDateTime(text) : UNAVAILABLE;
}

export function confidencePercent(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score * 100)));
}

function payloadRecord(payload: unknown): Record<string, unknown> | null {
  if (!isRecord(payload)) return null;
  if (isRecord(payload.batch)) {
    return { ...payload, ...payload.batch };
  }
  return payload;
}

export function readInvestigationBatch(payload: unknown): InvestigationBatchView {
  const record = payloadRecord(payload);
  if (!record) {
    return { batchId: null, analysisTimestamp: null, totalClustersAnalyzed: null, anomaliesDetected: null };
  }
  return {
    batchId: asString(record.batch_id),
    analysisTimestamp: asString(record.analysis_timestamp),
    totalClustersAnalyzed: asNumber(record.total_clusters_analyzed),
    anomaliesDetected: asNumber(record.anomalies_detected_count),
  };
}

function readThreats(payload: unknown): Record<string, unknown>[] {
  const record = payloadRecord(payload);
  const threats = record?.investigated_threats;
  if (!Array.isArray(threats)) return [];
  return threats.filter(isRecord);
}

export function mergeInvestigationFindings(
  audit: AgentAuditRunDetail,
  findings: AgentFindingRecord[],
  payload: unknown,
): InvestigationFindingView[] {
  const threats = readThreats(payload);
  if (findings.length > 0) {
    return findings.map((finding, index) => {
      const threat =
        threats.find((item) => asString(item.anomaly_id) === finding.external_anomaly_id) ??
        threats.find((item) => asString(item.sensor_cluster_id) === finding.external_cluster_id) ??
        null;
      return {
        key: finding.id || `${finding.external_anomaly_id}-${index}`,
        anomalyId: finding.external_anomaly_id,
        classification: finding.classification,
        severityTier: finding.severity_tier,
        confidence: finding.confidence_score,
        clusterId: finding.external_cluster_id,
        segmentId: finding.external_segment_id ?? asString(threat?.segment_id),
        valveId: finding.external_valve_id,
        mappingStatus: finding.mapping_status,
        mappedDetectionId: finding.mapped_detection_id,
        mappedSegmentId: finding.mapped_segment_id,
        mappedValveId: finding.mapped_valve_id,
        mappedSensorId: finding.mapped_sensor_id,
        justification: finding.operator_justification,
        physical: asJsonObject(finding.physical_deviations),
        criticality: asJsonObject(finding.criticality_metrics),
        network: asJsonObject(finding.network_status),
      };
    });
  }
  if (threats.length > 0) {
    return threats.map((threat, index) => ({
      key: asString(threat.anomaly_id) ?? `threat-${index}`,
      anomalyId: asString(threat.anomaly_id),
      classification: asString(threat.classification) ?? "unknown",
      severityTier: asNumber(threat.severity_tier) ?? 0,
      confidence: asNumber(threat.confidence_score),
      clusterId: asString(threat.sensor_cluster_id),
      segmentId: asString(threat.segment_id),
      valveId: isRecord(threat.criticality_metrics) ? asString(threat.criticality_metrics.associated_valve_id) : null,
      mappingStatus: "unmapped",
      mappedDetectionId: null,
      mappedSegmentId: null,
      mappedValveId: null,
      mappedSensorId: null,
      justification: asString(threat.operator_justification),
      physical: asJsonObject(threat.physical_deviations),
      criticality: asJsonObject(threat.criticality_metrics),
      network: asJsonObject(threat.network_status),
    }));
  }
  return audit.findings.map((finding, index) => ({
    key: `${finding.external_cluster_id ?? "finding"}-${index}`,
    anomalyId: finding.mapped_detection_id,
    classification: finding.classification,
    severityTier: finding.severity_tier,
    confidence: finding.confidence_score,
    clusterId: finding.external_cluster_id,
    segmentId: null,
    valveId: null,
    mappingStatus: finding.mapping_status,
    mappedDetectionId: finding.mapped_detection_id,
    mappedSegmentId: null,
    mappedValveId: null,
    mappedSensorId: null,
    justification: finding.operator_justification,
    physical: {},
    criticality: {},
    network: {},
  }));
}

export function readEstimatedVolumeLoss(physical: Record<string, JsonValue>): number | null {
  for (const key of ["estimated_volume_loss_m3", "estimated_volume_loss", "volume_loss_m3"]) {
    if (Object.prototype.hasOwnProperty.call(physical, key)) {
      return asNumber(physical[key]);
    }
  }
  return null;
}

export function networkField(network: Record<string, JsonValue>, ...keys: string[]): JsonValue | undefined {
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(network, key)) {
      return network[key];
    }
  }
  return undefined;
}

function reachabilityLabel(value: unknown): string | null {
  if (typeof value === "string") return value.replaceAll("_", " ");
  if (typeof value === "boolean") return value ? "Reachable" : "Unreachable";
  if (isRecord(value)) {
    if (typeof value.status === "string") return value.status.replaceAll("_", " ");
    if (typeof value.reachable === "boolean") return value.reachable ? "Reachable" : "Unreachable";
  }
  return null;
}

export function readReasoningSteps(trace: unknown): string[] {
  const cleaned = omitHiddenReasoning(sanitizeDisplayValue(trace));
  if (Array.isArray(cleaned)) {
    return cleaned
      .map((item) => {
        if (typeof item === "string") return item.trim();
        if (isRecord(item)) {
          const label = asString(item.step) ?? asString(item.summary) ?? asString(item.node) ?? asString(item.title);
          return label;
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
  }
  if (isRecord(cleaned)) {
    if (Array.isArray(cleaned.steps)) return readReasoningSteps(cleaned.steps);
    const label = asString(cleaned.summary) ?? asString(cleaned.text);
    return label ? [label] : [];
  }
  return [];
}

export function readOperatorMessage(payload: unknown): string | null {
  if (!isRecord(payload)) return null;
  const extensions = isRecord(payload.extensions) ? payload.extensions : null;
  return asString(payload.operator_message) ?? asString(extensions?.operator_message);
}

export function readBlockedReason(recommendation: AgentRecommendationRecord | null, payload: unknown): string | null {
  const isolation = recommendation?.decision === "AUTONOMOUS_ISOLATE";
  const blocked = recommendation?.safety_status === "blocked";
  if (!blocked && !isolation) return null;
  if (blocked) return "Blocked by AquaPulse safety policy";
  if (!isRecord(payload)) return null;
  const audit = isRecord(payload.audit) ? payload.audit : null;
  const denied = audit && isRecord(audit.network_denied) ? audit.network_denied : null;
  return asString(denied?.reason) ?? asString(audit?.actuation_result);
}

export function mergeResponseResult(
  audit: AgentAuditRunDetail,
  recommendations: AgentRecommendationRecord[],
  payload: unknown,
): ResponseResultView | null {
  const rec = recommendations[0] ?? null;
  const record = isRecord(payload) ? payload : null;
  if (!rec && !record && audit.recommendation_decisions.length === 0) {
    return null;
  }
  return {
    incidentId: rec?.external_incident_id ?? asString(record?.incident_id) ?? audit.related_incident,
    deviceId: rec?.external_device_id ?? asString(record?.device_id) ?? audit.related_device,
    clusterId: rec?.external_cluster_id ?? asString(record?.cluster_id) ?? audit.external_cluster_id,
    mappedIncident: rec?.mapped_incident_number ?? null,
    mappedDevice: rec?.mapped_device_id ?? null,
    severityTier: rec?.severity_tier ?? asNumber(record?.severity_tier) ?? audit.investigation_severity,
    reachability: reachabilityLabel(rec?.reachability ?? record?.reachability),
    decision: rec?.decision ?? audit.decision ?? asString(record?.decision),
    operatorMessage: readOperatorMessage(payload),
    humanOverrideRequested: rec?.human_override_requested ?? asBoolean(record?.human_override_requested),
    humanOverrideResponse: rec?.human_override_response ?? asString(record?.human_override_response),
    notificationSent: rec?.notification_sent ?? audit.notification_sent,
    valveCommandSent: rec?.valve_command_sent ?? audit.valve_command_sent,
    valveCommandConfirmed: rec?.valve_command_confirmed ?? audit.valve_command_confirmed,
    valveCommandVerified: rec?.valve_command_verified ?? false,
    createdAt: rec?.created_at ?? asString(record?.created_at) ?? null,
    safetyStatus: rec?.safety_status ?? audit.safety_status,
    reasoningSteps: readReasoningSteps(rec?.reasoning_trace ?? record?.reasoning_trace),
    blockedReason: readBlockedReason(rec, payload),
  };
}

export function mappingRows(
  findings: InvestigationFindingView[],
  response: ResponseResultView | null,
  warnings: unknown[],
): MappingRow[] {
  const rows: MappingRow[] = [];
  const seen = new Set<string>();
  const add = (row: MappingRow) => {
    const key = `${row.entityType}:${row.externalId}`;
    if (!row.externalId || seen.has(key)) return;
    seen.add(key);
    rows.push(row);
  };

  for (const finding of findings) {
    if (finding.clusterId) {
      add({
        entityType: "sensor_cluster",
        label: ENTITY_LABELS.sensor_cluster,
        externalId: finding.clusterId,
        mappedId: finding.mappedSensorId,
        mapped: Boolean(finding.mappedSensorId),
        href: finding.mappedSensorId ? `/assets/${encodeURIComponent(finding.mappedSensorId)}` : null,
      });
    }
    if (finding.segmentId) {
      add({
        entityType: "segment",
        label: ENTITY_LABELS.segment,
        externalId: finding.segmentId,
        mappedId: finding.mappedSegmentId,
        mapped: Boolean(finding.mappedSegmentId),
        href: finding.mappedSegmentId ? `/assets/${encodeURIComponent(finding.mappedSegmentId)}` : null,
      });
    }
    if (finding.valveId) {
      add({
        entityType: "valve",
        label: ENTITY_LABELS.valve,
        externalId: finding.valveId,
        mappedId: finding.mappedValveId,
        mapped: Boolean(finding.mappedValveId),
        href: finding.mappedValveId ? `/assets/${encodeURIComponent(finding.mappedValveId)}` : null,
      });
    }
    if (finding.anomalyId) {
      add({
        entityType: "detection",
        label: ENTITY_LABELS.detection,
        externalId: finding.anomalyId,
        mappedId: finding.mappedDetectionId,
        mapped: Boolean(finding.mappedDetectionId),
        href: finding.mappedDetectionId ? `/detections/${encodeURIComponent(finding.mappedDetectionId)}` : null,
      });
    }
  }

  if (response) {
    if (response.clusterId) {
      add({
        entityType: "sensor_cluster",
        label: ENTITY_LABELS.sensor_cluster,
        externalId: response.clusterId,
        mappedId: null,
        mapped: false,
        href: null,
      });
    }
    if (response.deviceId) {
      add({
        entityType: "device",
        label: ENTITY_LABELS.device,
        externalId: response.deviceId,
        mappedId: response.mappedDevice,
        mapped: Boolean(response.mappedDevice),
        href: response.mappedDevice ? `/assets/${encodeURIComponent(response.mappedDevice)}` : null,
      });
    }
    if (response.incidentId) {
      add({
        entityType: "incident",
        label: ENTITY_LABELS.incident,
        externalId: response.incidentId,
        mappedId: response.mappedIncident,
        mapped: Boolean(response.mappedIncident),
        href: response.mappedIncident ? `/incidents/${encodeURIComponent(response.mappedIncident)}` : null,
      });
    }
  }

  for (const warning of warnings) {
    if (!isRecord(warning)) continue;
    const externalId = asString(warning.external_id);
    const entityType = asString(warning.entity_type) ?? "identity";
    if (!externalId) continue;
    add({
      entityType,
      label: ENTITY_LABELS[entityType] ?? entityType.replaceAll("_", " "),
      externalId,
      mappedId: null,
      mapped: false,
      href: null,
    });
  }

  return rows;
}

export function mappingWarningMessages(warnings: unknown[]): string[] {
  return warnings
    .map((warning) => {
      if (typeof warning === "string") return warning;
      if (!isRecord(warning)) return null;
      const message = asString(warning.message);
      const entity = asString(warning.entity_type);
      const externalId = asString(warning.external_id);
      if (message && entity && externalId) {
        return `${ENTITY_LABELS[entity] ?? entity.replaceAll("_", " ")} ${externalId}: ${message}`;
      }
      return message;
    })
    .filter((item): item is string => Boolean(item));
}

export function validationLabel(run: AgentAuditRunDetail, integration: AgentRunDetail | null): string {
  if (integration && integration.validation_errors.length > 0) return "Validation failed";
  if (run.status === "rejected") return "Rejected";
  if (run.status === "validating") return "Validating";
  if (run.status === "failed") return "Failed";
  if (integration) return "Validated";
  return statusLabel(run.status);
}

export function rawPayload(integration: AgentRunDetail | null): JsonValue {
  if (!integration?.response_payload) return null;
  return sanitizeDisplayValue(omitHiddenReasoning(integration.response_payload as JsonValue));
}

export function eventWarning(event: AgentAuditEventDetail): string | null {
  if (event.error_message && event.error_message !== event.summary) {
    return event.error_message;
  }
  return null;
}

export {
  UNAVAILABLE,
  agentCodeLabel,
  auditTimelineHeading,
};
