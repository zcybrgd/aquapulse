import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { ALL_MAINTENANCE_TYPES, ALL_PRIORITIES, ALL_STATUSES } from "../lib/maintenance";
import type { AssetType } from "../types/assets";
import type { MaintenanceFilters, MaintenancePriority, MaintenanceType, WorkOrderSortField, WorkOrderStatus } from "../types/maintenance";

const EMPTY_FILTERS: MaintenanceFilters = {
  search: "",
  zone: "",
  asset_id: "",
  asset_type: "",
  maintenance_type: "",
  priority: "",
  status: "",
  overdue: false,
  assigned_to: "",
  sort_by: "due_at",
  sort_order: "asc",
};

const ASSET_TYPES: AssetType[] = ["sensor", "valve", "gateway"];
const SORT_FIELDS: WorkOrderSortField[] = ["due_at", "priority", "status", "created_at", "asset_name"];

function asAssetType(value: string | null): MaintenanceFilters["asset_type"] {
  return ASSET_TYPES.includes(value as AssetType) ? (value as AssetType) : "";
}

function asType(value: string | null): MaintenanceFilters["maintenance_type"] {
  return ALL_MAINTENANCE_TYPES.includes(value as MaintenanceType) ? (value as MaintenanceType) : "";
}

function asPriority(value: string | null): MaintenanceFilters["priority"] {
  return ALL_PRIORITIES.includes(value as MaintenancePriority) ? (value as MaintenancePriority) : "";
}

function asStatus(value: string | null): MaintenanceFilters["status"] {
  return ALL_STATUSES.includes(value as WorkOrderStatus) ? (value as WorkOrderStatus) : "";
}

function asSort(value: string | null): WorkOrderSortField {
  return SORT_FIELDS.includes(value as WorkOrderSortField) ? (value as WorkOrderSortField) : "due_at";
}

export function useMaintenanceFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<MaintenanceFilters>(
    () => ({
      search: searchParams.get("search") ?? "",
      zone: searchParams.get("zone") ?? "",
      asset_id: searchParams.get("asset_id") ?? "",
      asset_type: asAssetType(searchParams.get("asset_type")),
      maintenance_type: asType(searchParams.get("maintenance_type")),
      priority: asPriority(searchParams.get("priority")),
      status: asStatus(searchParams.get("status")),
      overdue: searchParams.get("overdue") === "true",
      assigned_to: searchParams.get("assigned_to") ?? "",
      sort_by: asSort(searchParams.get("sort_by")),
      sort_order: searchParams.get("sort_order") === "desc" ? "desc" : "asc",
    }),
    [searchParams],
  );

  const hasActiveFilters = Boolean(
    filters.search ||
      filters.zone ||
      filters.asset_id ||
      filters.asset_type ||
      filters.maintenance_type ||
      filters.priority ||
      filters.status ||
      filters.overdue ||
      filters.assigned_to ||
      filters.sort_by !== "due_at" ||
      filters.sort_order !== "asc",
  );

  const replaceParams = useCallback(
    (next: MaintenanceFilters) => {
      const params = new URLSearchParams();
      if (next.search.trim()) params.set("search", next.search.trim());
      if (next.zone) params.set("zone", next.zone);
      if (next.asset_id.trim()) params.set("asset_id", next.asset_id.trim());
      if (next.asset_type) params.set("asset_type", next.asset_type);
      if (next.maintenance_type) params.set("maintenance_type", next.maintenance_type);
      if (next.priority) params.set("priority", next.priority);
      if (next.status) params.set("status", next.status);
      if (next.overdue) params.set("overdue", "true");
      if (next.assigned_to.trim()) params.set("assigned_to", next.assigned_to.trim());
      if (next.sort_by !== "due_at") params.set("sort_by", next.sort_by);
      if (next.sort_order !== "asc") params.set("sort_order", next.sort_order);
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<MaintenanceFilters>) => {
      replaceParams({ ...filters, ...patch });
    },
    [filters, replaceParams],
  );

  return {
    filters,
    setFilters,
    clearFilters: () => replaceParams(EMPTY_FILTERS),
    hasActiveFilters,
  };
}
