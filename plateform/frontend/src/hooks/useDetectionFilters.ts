import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import {
  DEFAULT_DETECTION_SORT_BY,
  DEFAULT_DETECTION_SORT_ORDER,
  emptyDetectionFilters,
} from "../lib/detections";
import type {
  DetectionFilters,
  DetectionPriority,
  DetectionSortField,
  DetectionStatus,
  SortOrder,
} from "../types/detections";

const STATUSES: DetectionStatus[] = [
  "new",
  "queued",
  "under_review",
  "dismissed",
  "promoted",
  "merged",
];
const PRIORITIES: DetectionPriority[] = ["low", "medium", "high", "critical"];
const SORTS: DetectionSortField[] = ["detected_at", "priority", "score", "status"];

export function useDetectionFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<DetectionFilters>(() => {
    const status = searchParams.get("status");
    const priority = searchParams.get("priority");
    const sortBy = searchParams.get("sort_by");
    const sortOrder = searchParams.get("sort_order");
    return {
      search: searchParams.get("search") ?? "",
      status: STATUSES.includes(status as DetectionStatus) ? (status as DetectionStatus) : "",
      priority: PRIORITIES.includes(priority as DetectionPriority)
        ? (priority as DetectionPriority)
        : "",
      rule: searchParams.get("rule") ?? "",
      zone: searchParams.get("zone") ?? "",
      sensor: searchParams.get("sensor") ?? "",
      start: searchParams.get("start") ?? "",
      end: searchParams.get("end") ?? "",
      sort_by: SORTS.includes(sortBy as DetectionSortField)
        ? (sortBy as DetectionSortField)
        : DEFAULT_DETECTION_SORT_BY,
      sort_order:
        sortOrder === "asc" || sortOrder === "desc"
          ? (sortOrder as SortOrder)
          : DEFAULT_DETECTION_SORT_ORDER,
    };
  }, [searchParams]);

  const hasActiveFilters = Boolean(
    filters.search ||
      filters.status ||
      filters.priority ||
      filters.rule ||
      filters.zone ||
      filters.sensor ||
      filters.start ||
      filters.end ||
      filters.sort_by !== DEFAULT_DETECTION_SORT_BY ||
      filters.sort_order !== DEFAULT_DETECTION_SORT_ORDER,
  );

  const replaceParams = useCallback(
    (next: DetectionFilters) => {
      const params = new URLSearchParams();
      if (next.search.trim()) params.set("search", next.search.trim());
      if (next.status) params.set("status", next.status);
      if (next.priority) params.set("priority", next.priority);
      if (next.rule) params.set("rule", next.rule);
      if (next.zone) params.set("zone", next.zone);
      if (next.sensor) params.set("sensor", next.sensor);
      if (next.start) params.set("start", next.start);
      if (next.end) params.set("end", next.end);
      if (next.sort_by !== DEFAULT_DETECTION_SORT_BY) params.set("sort_by", next.sort_by);
      if (next.sort_order !== DEFAULT_DETECTION_SORT_ORDER) params.set("sort_order", next.sort_order);
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<DetectionFilters>) => replaceParams({ ...filters, ...patch }),
    [filters, replaceParams],
  );

  const clearFilters = useCallback(() => replaceParams(emptyDetectionFilters()), [replaceParams]);

  return { filters, setFilters, clearFilters, hasActiveFilters };
}
