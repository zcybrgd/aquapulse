import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { ALL_INCIDENT_STATUSES } from "../lib/incidents";
import type { IncidentStatus, OperationsFilters, SeverityTier } from "../types/incidents";

const EMPTY_FILTERS: OperationsFilters = {
  search: "",
  severity: "",
  status: "",
  zone: "",
  assigned_to: "",
};

function asSeverity(value: string | null): OperationsFilters["severity"] {
  if (value === "tier_1" || value === "tier_2" || value === "tier_3") {
    return value as SeverityTier;
  }
  return "";
}

function asStatus(value: string | null): OperationsFilters["status"] {
  return ALL_INCIDENT_STATUSES.includes(value as IncidentStatus) ? (value as IncidentStatus) : "";
}

export function useOperationsFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<OperationsFilters>(
    () => ({
      search: searchParams.get("search") ?? "",
      severity: asSeverity(searchParams.get("severity")),
      status: asStatus(searchParams.get("status")),
      zone: searchParams.get("zone") ?? "",
      assigned_to: searchParams.get("assigned_to") ?? "",
    }),
    [searchParams],
  );

  const hasActiveFilters = Boolean(
    filters.search || filters.severity || filters.status || filters.zone || filters.assigned_to,
  );

  const replaceParams = useCallback(
    (next: OperationsFilters) => {
      const params = new URLSearchParams();
      if (next.search.trim()) params.set("search", next.search.trim());
      if (next.severity) params.set("severity", next.severity);
      if (next.status) params.set("status", next.status);
      if (next.zone) params.set("zone", next.zone);
      if (next.assigned_to.trim()) params.set("assigned_to", next.assigned_to.trim());
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<OperationsFilters>) => {
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
