import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { DEFAULT_SORT_BY, DEFAULT_SORT_ORDER } from "../lib/incidents";
import type {
  IncidentClassification,
  IncidentFilters,
  IncidentSortField,
  IncidentStatus,
  SortOrder,
} from "../types/incidents";

const EMPTY_FILTERS: IncidentFilters = {
  search: "",
  severity: "",
  status: "",
  classification: "",
  zone: "",
  sort_by: DEFAULT_SORT_BY,
  sort_order: DEFAULT_SORT_ORDER,
};

function asSeverity(value: string | null): IncidentFilters["severity"] {
  if (value === "tier_1" || value === "tier_2" || value === "tier_3") {
    return value;
  }
  return "";
}

function asStatus(value: string | null): IncidentFilters["status"] {
  const allowed: IncidentStatus[] = [
    "investigating",
    "awaiting_approval",
    "resolved",
  ];
  return allowed.includes(value as IncidentStatus) ? (value as IncidentStatus) : "";
}

function asClassification(value: string | null): IncidentFilters["classification"] {
  const allowed: IncidentClassification[] = [
    "confirmed_leak",
    "suspected_leak",
    "connectivity_degradation",
    "sensor_fault",
    "pressure_anomaly",
    "normal_demand_spike",
    "insufficient_data",
  ];
  return allowed.includes(value as IncidentClassification)
    ? (value as IncidentClassification)
    : "";
}

function asSortField(value: string | null): IncidentSortField {
  const allowed: IncidentSortField[] = [
    "detected_at",
    "severity",
    "status",
    "priority",
  ];
  return allowed.includes(value as IncidentSortField)
    ? (value as IncidentSortField)
    : DEFAULT_SORT_BY;
}

function asSortOrder(value: string | null): SortOrder {
  return value === "asc" || value === "desc" ? value : DEFAULT_SORT_ORDER;
}

export function useIncidentFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<IncidentFilters>(
    () => ({
      search: searchParams.get("search") ?? "",
      severity: asSeverity(searchParams.get("severity")),
      status: asStatus(searchParams.get("status")),
      classification: asClassification(searchParams.get("classification")),
      zone: searchParams.get("zone") ?? "",
      sort_by: asSortField(searchParams.get("sort_by")),
      sort_order: asSortOrder(searchParams.get("sort_order")),
    }),
    [searchParams],
  );

  const hasActiveFilters = Boolean(
    filters.search ||
      filters.severity ||
      filters.status ||
      filters.classification ||
      filters.zone ||
      filters.sort_by !== DEFAULT_SORT_BY ||
      filters.sort_order !== DEFAULT_SORT_ORDER,
  );

  const replaceParams = useCallback(
    (next: IncidentFilters) => {
      const params = new URLSearchParams();
      if (next.search.trim()) {
        params.set("search", next.search.trim());
      }
      if (next.severity) {
        params.set("severity", next.severity);
      }
      if (next.status) {
        params.set("status", next.status);
      }
      if (next.classification) {
        params.set("classification", next.classification);
      }
      if (next.zone) {
        params.set("zone", next.zone);
      }
      if (next.sort_by !== DEFAULT_SORT_BY) {
        params.set("sort_by", next.sort_by);
      }
      if (next.sort_order !== DEFAULT_SORT_ORDER) {
        params.set("sort_order", next.sort_order);
      }
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<IncidentFilters>) => {
      replaceParams({ ...filters, ...patch });
    },
    [filters, replaceParams],
  );

  const clearFilters = useCallback(() => {
    replaceParams(EMPTY_FILTERS);
  }, [replaceParams]);

  return { filters, setFilters, clearFilters, hasActiveFilters };
}

export function emptyIncidentFilters(): IncidentFilters {
  return { ...EMPTY_FILTERS };
}
