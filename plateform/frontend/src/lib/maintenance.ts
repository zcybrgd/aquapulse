import type {
  CompletionResult,
  MaintenancePriority,
  MaintenanceType,
  WorkOrderStatus,
} from "../types/maintenance";

export const MAINTENANCE_TYPE_LABELS: Record<MaintenanceType, string> = {
  preventive: "Preventive",
  inspection: "Inspection",
  calibration: "Calibration",
  battery_replacement: "Battery replacement",
  connectivity_check: "Connectivity check",
  corrective: "Corrective",
};

export const PRIORITY_LABELS: Record<MaintenancePriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const STATUS_LABELS: Record<WorkOrderStatus, string> = {
  scheduled: "Scheduled",
  assigned: "Assigned",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

export const COMPLETION_LABELS: Record<CompletionResult, string> = {
  completed_successfully: "Completed successfully",
  follow_up_required: "Follow-up required",
  asset_repaired: "Asset repaired",
  asset_replaced: "Asset replaced",
  no_fault_found: "No fault found",
  unable_to_complete: "Unable to complete",
  other: "Other",
};

export const ALL_MAINTENANCE_TYPES = Object.keys(MAINTENANCE_TYPE_LABELS) as MaintenanceType[];
export const ALL_PRIORITIES = Object.keys(PRIORITY_LABELS) as MaintenancePriority[];
export const ALL_STATUSES = Object.keys(STATUS_LABELS) as WorkOrderStatus[];
export const ALL_COMPLETION_RESULTS = Object.keys(COMPLETION_LABELS) as CompletionResult[];

export const EVENT_LABELS: Record<string, string> = {
  work_order_created: "Work order created",
  work_order_assigned: "Assigned",
  work_order_rescheduled: "Rescheduled",
  work_started: "Work started",
  note_added: "Note added",
  work_completed: "Work completed",
  work_cancelled: "Work cancelled",
  plan_created: "Plan created",
  plan_updated: "Plan updated",
  plan_disabled: "Plan disabled",
};

export function primaryWorkOrderAction(actions: string[]): { action: string; label: string } {
  if (actions.includes("start")) return { action: "start", label: "Start work" };
  if (actions.includes("assign")) return { action: "assign", label: "Assign" };
  if (actions.includes("complete")) return { action: "complete", label: "Complete" };
  if (actions.includes("reschedule")) return { action: "reschedule", label: "Reschedule" };
  return { action: "view", label: "View details" };
}

export const NO_PHYSICAL_ACTION =
  "Completing this record does not execute a physical device command.";

export function toDateTimeLocal(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function fromDateTimeLocal(value: string): string {
  return new Date(value).toISOString();
}
