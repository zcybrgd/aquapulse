import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { NetworkFilters } from "../types/networkHealth";

const EMPTY: NetworkFilters = {
  event_type: "",
  status: "",
  device: "",
  cluster: "",
  incident: "",
  search: "",
  start: "",
  end: "",
};

export function useNetworkHealthFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo<NetworkFilters>(
    () => ({
      event_type: searchParams.get("event_type") ?? "",
      status: searchParams.get("status") ?? "",
      device: searchParams.get("device") ?? "",
      cluster: searchParams.get("cluster") ?? "",
      incident: searchParams.get("incident") ?? "",
      search: searchParams.get("q") ?? "",
      start: searchParams.get("start") ?? "",
      end: searchParams.get("end") ?? "",
    }),
    [searchParams],
  );

  const replaceParams = useCallback(
    (next: NetworkFilters) => {
      const params = new URLSearchParams();
      if (next.event_type.trim()) params.set("event_type", next.event_type.trim());
      if (next.status.trim()) params.set("status", next.status.trim());
      if (next.device.trim()) params.set("device", next.device.trim());
      if (next.cluster.trim()) params.set("cluster", next.cluster.trim());
      if (next.incident.trim()) params.set("incident", next.incident.trim());
      if (next.search.trim()) params.set("q", next.search.trim());
      if (next.start.trim()) params.set("start", next.start.trim());
      if (next.end.trim()) params.set("end", next.end.trim());
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<NetworkFilters>) => replaceParams({ ...filters, ...patch }),
    [filters, replaceParams],
  );

  return {
    filters,
    setFilters,
    clearFilters: () => replaceParams(EMPTY),
    hasActiveFilters: Object.values(filters).some((value) => value.trim()),
  };
}
