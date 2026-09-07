import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { NetworkFilters } from "../types/networkHealth";

const EMPTY: NetworkFilters = {
  search: "",
  zone: "",
  asset_type: "",
  reachability: "",
  location_available: "",
  cellular_available: "",
  source_mode: "",
  device: "",
};

export function useNetworkHealthFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo<NetworkFilters>(
    () => ({
      search: searchParams.get("q") ?? "",
      zone: searchParams.get("zone") ?? "",
      asset_type: searchParams.get("type") ?? "",
      reachability: searchParams.get("reachability") ?? "",
      location_available: searchParams.get("location") ?? "",
      cellular_available: searchParams.get("cellular") ?? "",
      source_mode: searchParams.get("source") ?? "",
      device: searchParams.get("device") ?? "",
    }),
    [searchParams],
  );

  const replaceParams = useCallback(
    (next: NetworkFilters) => {
      const params = new URLSearchParams();
      if (next.search.trim()) params.set("q", next.search.trim());
      if (next.zone.trim()) params.set("zone", next.zone.trim());
      if (next.asset_type.trim()) params.set("type", next.asset_type.trim());
      if (next.reachability.trim()) params.set("reachability", next.reachability.trim());
      if (next.location_available.trim()) params.set("location", next.location_available.trim());
      if (next.cellular_available.trim()) params.set("cellular", next.cellular_available.trim());
      if (next.source_mode.trim()) params.set("source", next.source_mode.trim());
      if (next.device.trim()) params.set("device", next.device.trim());
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
    clearFilters: () => replaceParams({ ...EMPTY, device: filters.device }),
    hasActiveFilters: [
      filters.search,
      filters.zone,
      filters.asset_type,
      filters.reachability,
      filters.location_available,
      filters.cellular_available,
      filters.source_mode,
    ].some((value) => value.trim()),
  };
}
