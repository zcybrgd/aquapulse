import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { AnalyticsFilters, AnalyticsRange } from "../types/analytics";

const RANGES: AnalyticsRange[] = ["24h", "7d", "30d"];

const EMPTY: AnalyticsFilters = {
  range: "24h",
  zone: "",
  sensor: "",
};

function asRange(value: string | null): AnalyticsRange {
  return RANGES.includes(value as AnalyticsRange) ? (value as AnalyticsRange) : "24h";
}

export function useAnalyticsFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<AnalyticsFilters>(
    () => ({
      range: asRange(searchParams.get("range")),
      zone: searchParams.get("zone") ?? "",
      sensor: searchParams.get("sensor") ?? "",
    }),
    [searchParams],
  );

  const replaceParams = useCallback(
    (next: AnalyticsFilters) => {
      const params = new URLSearchParams();
      if (next.range !== "24h") params.set("range", next.range);
      if (next.zone.trim()) params.set("zone", next.zone.trim());
      if (next.sensor.trim()) params.set("sensor", next.sensor.trim());
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<AnalyticsFilters>) => {
      replaceParams({ ...filters, ...patch });
    },
    [filters, replaceParams],
  );

  return {
    filters,
    setFilters,
    clearFilters: () => replaceParams(EMPTY),
    hasActiveFilters: Boolean(filters.zone || filters.sensor || filters.range !== "24h"),
  };
}
