import type {
  IncidentCenterStats,
  IncidentClassification,
  IncidentSortField,
  IncidentStatus,
  IncidentSummary,
  SeverityTier,
  TimelineSource,
} from "../types/incidents";
import { isSameLocalDay } from "./format";

export const DEFAULT_SORT_BY: IncidentSortField = "priority";
export const DEFAULT_SORT_ORDER = "desc" as const;

export const SEVERITY_LABELS: Record<SeverityTier, string> = {
  tier_1: "Tier 1",
  tier_2: "Tier 2",
  tier_3: "Tier 3",
};

export const CLASSIFICATION_LABELS: Record<IncidentClassification, string> = {
  confirmed_leak: "Confirmed leak",
  suspected_leak: "Suspected leak",
  connectivity_degradation: "Connectivity degradation",
  sensor_fault: "Sensor fault",
  pressure_anomaly: "Pressure anomaly",
  normal_demand_spike: "Normal demand spike",
  insufficient_data: "Insufficient data",
};

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  investigating: "Investigating",
  awaiting_approval: "Waiting for approval",
  resolved: "Resolved",
};

export const RESOLUTION_LABELS: Record<string, string> = {
  leak_repaired: "Leak repaired",
  isolated_for_maintenance: "Isolated for maintenance",
  sensor_fault: "Sensor fault",
  planned_operation: "Planned operation",
  false_alarm: "False alarm",
  monitoring_completed: "Monitoring completed",
  other: "Other",
};

export const TASK_STATUS_LABELS: Record<string, string> = {
  todo: "To do",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

export const TASK_PRIORITY_LABELS: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const SOURCE_LABELS: Record<TimelineSource, string> = {
  detector: "Detector",
  agent: "Agent",
  network: "Network",
  operator: "Operator",
  system: "System",
};

export const SORT_LABELS: Record<IncidentSortField, string> = {
  priority: "Priority",
  detected_at: "Detected time",
  severity: "Severity",
  status: "Status",
};

export const ACTIVE_STATUSES: IncidentStatus[] = [
  "investigating",
  "awaiting_approval",
];

export const ACTION_DISABLED_HINT =
  "Operational command integration not enabled. This control does not send a physical command.";

export const ALL_INCIDENT_STATUSES: IncidentStatus[] = [
  "investigating",
  "awaiting_approval",
  "resolved",
];

export function operationsPrimaryAction(
  actions: string[],
  status?: IncidentStatus,
): { kind: string; label: string } {
  if (status === "awaiting_approval" && actions.includes("start_response")) {
    return { kind: "start_response", label: "Approve and start response" };
  }
  if (actions.includes("acknowledge")) {
    return { kind: "acknowledge", label: "Acknowledge" };
  }
  if (actions.includes("start_investigation")) {
    return { kind: "start_investigation", label: "Start investigation" };
  }
  if (actions.includes("return_investigation")) {
    return { kind: "start_investigation", label: "Return to investigation" };
  }
  if (actions.includes("start_response")) {
    return { kind: "start_response", label: "Start response" };
  }
  if (actions.includes("request_approval")) {
    return { kind: "request_approval", label: "Request approval" };
  }
  if (actions.includes("manage_tasks")) {
    return { kind: "open", label: "Manage response" };
  }
  if (actions.includes("reopen")) {
    return { kind: "open", label: "View incident" };
  }
  return { kind: "open", label: "Open incident" };
}

export function isActiveIncident(incident: IncidentSummary): boolean {
  return ACTIVE_STATUSES.includes(incident.status);
}

export function computeIncidentStats(items: IncidentSummary[]): IncidentCenterStats {
  return {
    total: items.length,
    critical: items.filter((item) => item.severity === "tier_3").length,
    awaitingApproval: items.filter((item) => item.status === "awaiting_approval").length,
    investigating: items.filter((item) => item.status === "investigating").length,
    resolvedToday: items.filter(
      (item) => item.status === "resolved" && isSameLocalDay(item.updated_at),
    ).length,
    active: items.filter(isActiveIncident).length,
  };
}

export function uniqueZones(items: IncidentSummary[]): string[] {
  return [...new Set(items.map((item) => item.zone))].sort((a, b) => a.localeCompare(b));
}
