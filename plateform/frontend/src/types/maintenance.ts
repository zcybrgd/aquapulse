import type { AssetType } from "./assets";

export type MaintenanceType =
  | "preventive"
  | "inspection"
  | "calibration"
  | "battery_replacement"
  | "connectivity_check"
  | "corrective";

export type MaintenancePriority = "low" | "medium" | "high" | "critical";

export type WorkOrderStatus = "scheduled" | "assigned" | "in_progress" | "completed" | "cancelled";

export type CompletionResult =
  | "completed_successfully"
  | "follow_up_required"
  | "asset_repaired"
  | "asset_replaced"
  | "no_fault_found"
  | "unable_to_complete"
  | "other";

export type WorkOrderSortField = "due_at" | "priority" | "status" | "created_at" | "asset_name";

export interface MaintenanceFilters {
  search: string;
  zone: string;
  asset_id: string;
  asset_type: AssetType | "";
  maintenance_type: MaintenanceType | "";
  priority: MaintenancePriority | "";
  status: WorkOrderStatus | "";
  overdue: boolean;
  assigned_to: string;
  sort_by: WorkOrderSortField;
  sort_order: "asc" | "desc";
}

export interface MaintenanceSummary {
  overdue: number;
  due_within_7_days: number;
  in_progress: number;
  completed_in_period: number;
  critical: number;
  assets_without_plan: number;
  open_work_orders: number;
  reference_time: string;
}

export interface WorkOrderSummary {
  id: string;
  public_id: string;
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  zone: string;
  zone_id: string;
  location_label: string | null;
  has_cellular_identity: boolean;
  device_msisdn_masked: string | null;
  maintenance_plan_id: string | null;
  incident_id: string | null;
  maintenance_type: MaintenanceType;
  title: string;
  description: string | null;
  instructions: string | null;
  priority: MaintenancePriority;
  status: WorkOrderStatus;
  assigned_to: string | null;
  scheduled_start_at: string | null;
  due_at: string;
  started_at: string | null;
  completed_at: string | null;
  completed_by: string | null;
  cancelled_at: string | null;
  cancelled_by: string | null;
  cancellation_reason: string | null;
  completion_summary: string | null;
  completion_result: CompletionResult | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  overdue: boolean;
  allowed_actions: string[];
}

export interface WorkOrderHistoryEvent {
  id: string;
  public_id: string;
  event_type: string;
  from_status: WorkOrderStatus | null;
  to_status: WorkOrderStatus | null;
  actor_name: string;
  note: string | null;
  created_at: string;
}

export interface WorkOrderDetail extends WorkOrderSummary {
  history: WorkOrderHistoryEvent[];
}

export interface WorkOrderListResponse {
  items: WorkOrderSummary[];
  total: number;
  summary: MaintenanceSummary;
  reference_time: string;
}

export interface MaintenancePlanSummary {
  id: string;
  public_id: string;
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  zone: string;
  name: string;
  maintenance_type: MaintenanceType;
  interval_days: number;
  priority: MaintenancePriority;
  instructions: string | null;
  enabled: boolean;
  last_generated_at: string | null;
  next_due_at: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AssetMaintenanceResponse {
  asset_id: string;
  overdue: boolean;
  last_maintenance_at: string | null;
  next_maintenance_at: string | null;
  active_plans: MaintenancePlanSummary[];
  open_work_orders: WorkOrderSummary[];
  recent_completed: WorkOrderSummary[];
  reference_time: string;
}

export interface IncidentMaintenanceResponse {
  incident_id: string;
  items: WorkOrderSummary[];
  total: number;
  reference_time: string;
}

export interface UpcomingMaintenanceItem {
  id: string;
  kind: string;
  title: string;
  asset_id: string;
  asset_name: string;
  zone: string;
  due_at: string;
  priority: MaintenancePriority;
  maintenance_type: MaintenanceType;
  status: string | null;
  overdue: boolean;
}
