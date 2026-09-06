import type { AssetMaintenanceResponse, IncidentMaintenanceResponse, MaintenanceFilters, UpcomingMaintenanceItem, WorkOrderDetail, WorkOrderListResponse } from "../types/maintenance";
import { apiClient } from "./client";

export function toMaintenanceQuery(filters: MaintenanceFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.search.trim()) query.search = filters.search.trim();
  if (filters.zone) query.zone = filters.zone;
  if (filters.asset_id.trim()) query.asset_id = filters.asset_id.trim();
  if (filters.asset_type) query.asset_type = filters.asset_type;
  if (filters.maintenance_type) query.maintenance_type = filters.maintenance_type;
  if (filters.priority) query.priority = filters.priority;
  if (filters.status) query.status = filters.status;
  if (filters.overdue) query.overdue = "true";
  if (filters.assigned_to.trim()) query.assigned_to = filters.assigned_to.trim();
  if (filters.sort_by !== "due_at") query.sort_by = filters.sort_by;
  if (filters.sort_order !== "asc") query.sort_order = filters.sort_order;
  return query;
}

export async function fetchWorkOrders(filters: MaintenanceFilters): Promise<WorkOrderListResponse> {
  const { data } = await apiClient.get<WorkOrderListResponse>("/api/maintenance/work-orders", {
    params: toMaintenanceQuery(filters),
  });
  return data;
}

export async function fetchUpcomingMaintenance(): Promise<UpcomingMaintenanceItem[]> {
  const { data } = await apiClient.get<UpcomingMaintenanceItem[]>("/api/maintenance/work-orders/upcoming");
  return data;
}

export async function fetchWorkOrder(workOrderId: string): Promise<WorkOrderDetail> {
  const { data } = await apiClient.get<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(workOrderId)}`,
  );
  return data;
}

export async function fetchAssetMaintenance(assetId: string): Promise<AssetMaintenanceResponse> {
  const { data } = await apiClient.get<AssetMaintenanceResponse>(
    `/api/assets/${encodeURIComponent(assetId)}/maintenance`,
  );
  return data;
}

export async function fetchIncidentMaintenance(incidentId: string): Promise<IncidentMaintenanceResponse> {
  const { data } = await apiClient.get<IncidentMaintenanceResponse>(
    `/api/incidents/${encodeURIComponent(incidentId)}/maintenance`,
  );
  return data;
}

export async function createWorkOrder(payload: Record<string, unknown>): Promise<WorkOrderDetail> {
  const { data } = await apiClient.post<WorkOrderDetail>("/api/maintenance/work-orders", payload);
  return data;
}

export async function assignWorkOrder(id: string, actorName: string, assignedTo: string, note?: string) {
  const { data } = await apiClient.post<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(id)}/assign`,
    { actor_name: actorName, assigned_to: assignedTo, note },
  );
  return data;
}

export async function rescheduleWorkOrder(id: string, actorName: string, dueAt: string, note?: string) {
  const { data } = await apiClient.post<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(id)}/reschedule`,
    { actor_name: actorName, due_at: dueAt, note },
  );
  return data;
}

export async function startWorkOrder(
  id: string,
  actorName: string,
  options: { assignedTo?: string; confirmUnassigned?: boolean; note?: string } = {},
) {
  const { data } = await apiClient.post<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(id)}/start`,
    {
      actor_name: actorName,
      assigned_to: options.assignedTo,
      confirm_unassigned: options.confirmUnassigned ?? false,
      note: options.note,
    },
  );
  return data;
}

export async function addWorkOrderNote(id: string, actorName: string, note: string) {
  const { data } = await apiClient.post<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(id)}/notes`,
    { actor_name: actorName, note },
  );
  return data;
}

export async function completeWorkOrder(
  id: string,
  actorName: string,
  completionResult: string,
  completionSummary: string,
) {
  const { data } = await apiClient.post<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(id)}/complete`,
    {
      actor_name: actorName,
      completion_result: completionResult,
      completion_summary: completionSummary,
      confirm: true,
    },
  );
  return data;
}

export async function cancelWorkOrder(id: string, actorName: string, reason: string) {
  const { data } = await apiClient.post<WorkOrderDetail>(
    `/api/maintenance/work-orders/${encodeURIComponent(id)}/cancel`,
    { actor_name: actorName, reason, confirm: true },
  );
  return data;
}
