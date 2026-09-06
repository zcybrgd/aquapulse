import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { DEFAULT_ASSET_SORT_BY, DEFAULT_ASSET_SORT_ORDER } from "../lib/assets";
import type {
  AssetFilters,
  AssetSortField,
  AssetType,
  MaintenanceFilter,
  OperationalStatus,
  SortOrder,
} from "../types/assets";

const EMPTY_FILTERS: AssetFilters = {
  search: "",
  asset_type: "",
  status: "",
  zone: "",
  maintenance: "",
  sort_by: DEFAULT_ASSET_SORT_BY,
  sort_order: DEFAULT_ASSET_SORT_ORDER,
};

function asType(value: string | null): AssetFilters["asset_type"] {
  const allowed: AssetType[] = ["sensor", "valve", "gateway"];
  return allowed.includes(value as AssetType) ? (value as AssetType) : "";
}

function asStatus(value: string | null): AssetFilters["status"] {
  const allowed: OperationalStatus[] = ["online", "degraded", "offline"];
  return allowed.includes(value as OperationalStatus) ? (value as OperationalStatus) : "";
}

function asMaintenance(value: string | null): MaintenanceFilter {
  const allowed: MaintenanceFilter[] = ["due", "upcoming", "scheduled"];
  return allowed.includes(value as MaintenanceFilter) ? (value as MaintenanceFilter) : "";
}

function asSortField(value: string | null): AssetSortField {
  const allowed: AssetSortField[] = [
    "name",
    "asset_type",
    "status",
    "health_score",
    "last_seen",
    "next_maintenance",
  ];
  return allowed.includes(value as AssetSortField) ? (value as AssetSortField) : DEFAULT_ASSET_SORT_BY;
}

function asSortOrder(value: string | null): SortOrder {
  return value === "asc" || value === "desc" ? value : DEFAULT_ASSET_SORT_ORDER;
}

export function useAssetFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<AssetFilters>(
    () => ({
      search: searchParams.get("search") ?? "",
      asset_type: asType(searchParams.get("asset_type")),
      status: asStatus(searchParams.get("status")),
      zone: searchParams.get("zone") ?? "",
      maintenance: asMaintenance(searchParams.get("maintenance")),
      sort_by: asSortField(searchParams.get("sort_by")),
      sort_order: asSortOrder(searchParams.get("sort_order")),
    }),
    [searchParams],
  );

  const hasActiveFilters = Boolean(
    filters.search ||
      filters.asset_type ||
      filters.status ||
      filters.zone ||
      filters.maintenance ||
      filters.sort_by !== DEFAULT_ASSET_SORT_BY ||
      filters.sort_order !== DEFAULT_ASSET_SORT_ORDER,
  );

  const replaceParams = useCallback(
    (next: AssetFilters) => {
      const params = new URLSearchParams();
      if (next.search.trim()) {
        params.set("search", next.search.trim());
      }
      if (next.asset_type) {
        params.set("asset_type", next.asset_type);
      }
      if (next.status) {
        params.set("status", next.status);
      }
      if (next.zone) {
        params.set("zone", next.zone);
      }
      if (next.maintenance) {
        params.set("maintenance", next.maintenance);
      }
      if (next.sort_by !== DEFAULT_ASSET_SORT_BY) {
        params.set("sort_by", next.sort_by);
      }
      if (next.sort_order !== DEFAULT_ASSET_SORT_ORDER) {
        params.set("sort_order", next.sort_order);
      }
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<AssetFilters>) => {
      replaceParams({ ...filters, ...patch });
    },
    [filters, replaceParams],
  );

  const clearFilters = useCallback(() => {
    replaceParams(EMPTY_FILTERS);
  }, [replaceParams]);

  return { filters, setFilters, clearFilters, hasActiveFilters };
}

export function emptyAssetFilters(): AssetFilters {
  return { ...EMPTY_FILTERS };
}
