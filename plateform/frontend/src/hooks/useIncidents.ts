import { useCallback, useEffect, useState } from "react";

import { fetchIncidents } from "../api/incidents";
import { computeIncidentStats, isActiveIncident, uniqueZones } from "../lib/incidents";
import type {
  IncidentCenterStats,
  IncidentFilters,
  IncidentSummary,
} from "../types/incidents";
import { emptyIncidentFilters } from "./useIncidentFilters";

interface IncidentListState {
  items: IncidentSummary[];
  allItems: IncidentSummary[];
  total: number;
  stats: IncidentCenterStats;
  zones: string[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useIncidents(filters: IncidentFilters): IncidentListState {
  const [items, setItems] = useState<IncidentSummary[]>([]);
  const [allItems, setAllItems] = useState<IncidentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [filtered, all] = await Promise.all([
        fetchIncidents(filters),
        fetchIncidents(emptyIncidentFilters()),
      ]);
      setItems(filtered.items);
      setTotal(filtered.total);
      setAllItems(all.items);
    } catch {
      setItems([]);
      setAllItems([]);
      setTotal(0);
      setError(
        "We could not load incidents from the AquaPulse service. Confirm the API is running, then try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    items,
    allItems,
    total,
    stats: computeIncidentStats(allItems),
    zones: uniqueZones(allItems),
    loading,
    error,
    reload: () => void load(),
  };
}

export function useIncidentPreview() {
  const [items, setItems] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchIncidents({
        ...emptyIncidentFilters(),
        sort_by: "priority",
        sort_order: "desc",
      });
      setItems(response.items.filter(isActiveIncident).slice(0, 3));
    } catch {
      setItems([]);
      setError("Incident preview is unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { items, loading, error, reload: () => void load() };
}
