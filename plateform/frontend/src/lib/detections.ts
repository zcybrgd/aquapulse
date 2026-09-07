import type {
  DetectionFilters,
  DetectionPriority,
  DetectionSortField,
  DetectionStatus,
  DismissalReason,
  InvestigationEventType,
} from "../types/detections";

export const DEFAULT_DETECTION_SORT_BY: DetectionSortField = "detected_at";
export const DEFAULT_DETECTION_SORT_ORDER = "desc" as const;

export const STATUS_LABELS: Record<DetectionStatus, string> = {
  new: "New",
  queued: "Queued",
  under_review: "Under review",
  dismissed: "Dismissed",
  promoted: "Promoted",
  merged: "Merged",
};

export const PRIORITY_LABELS: Record<DetectionPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const RULE_LABELS: Record<string, string> = {
  PRESSURE_DROP: "Rapid pressure drop",
  FLOW_SURGE: "Rapid flow surge",
  COMBINED_LEAK_PATTERN: "Combined pressure and flow",
  CONNECTIVITY_DEGRADATION: "Connectivity degradation",
  MISSING_TELEMETRY: "Missing telemetry",
  SENSOR_QUALITY: "Sensor quality",
};

export const SORT_LABELS: Record<DetectionSortField, string> = {
  detected_at: "Detected time",
  priority: "Screening priority",
  score: "Score",
  status: "Status",
};

export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  first_value: "First value",
  last_value: "Last value",
  absolute_change: "Absolute change",
  percent_change: "Percentage change",
  threshold_exceeded: "Threshold comparison",
  intermittent_gap: "Measurement gap",
  missing_reading: "Missing reading",
  out_of_range: "Outside valid range",
  frozen_value: "Frozen value",
  inconsistent_ratio: "Internal inconsistency",
};

export function scorePercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function emptyDetectionFilters(): DetectionFilters {
  return {
    search: "",
    status: "",
    priority: "",
    rule: "",
    zone: "",
    sensor: "",
    start: "",
    end: "",
    sort_by: DEFAULT_DETECTION_SORT_BY,
    sort_order: DEFAULT_DETECTION_SORT_ORDER,
  };
}

export const DISMISSAL_LABELS: Record<DismissalReason, string> = {
  false_positive: "False positive",
  sensor_fault: "Sensor fault",
  planned_operation: "Planned operation",
  duplicate: "Duplicate",
  insufficient_evidence: "Insufficient evidence",
  other: "Other",
};

export const EVENT_LABELS: Record<InvestigationEventType, string> = {
  review_started: "Review started",
  note_added: "Note added",
  dismissed: "Dismissed",
  reopened: "Reopened",
  merged: "Merged",
  promoted: "Promoted to incident",
};

export const TERMINAL_STATUSES: DetectionStatus[] = ["dismissed", "promoted", "merged"];

export function isTerminalDetection(status: DetectionStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}

export function queuePrimaryAction(item: { status: DetectionStatus; incident_id: string | null; merged_into_detection_id: string | null }): {
  kind: "start_review" | "continue_review" | "view_incident" | "view_merged" | "view";
  label: string;
} {
  if (item.status === "promoted" && item.incident_id) {
    return { kind: "view_incident", label: "View incident" };
  }
  if (item.status === "merged" && item.merged_into_detection_id) {
    return { kind: "view_merged", label: "View merged detection" };
  }
  if (item.status === "under_review") {
    return { kind: "continue_review", label: "Continue review" };
  }
  if (item.status === "new" || item.status === "queued") {
    return { kind: "start_review", label: "Start review" };
  }
  return { kind: "view", label: "View details" };
}
