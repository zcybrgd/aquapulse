import { useCallback, useEffect, useState } from "react";

import { fetchAssets } from "../api/assets";
import { uniqueAssetZones } from "../lib/assets";
import type { AssetFilters, AssetListSummary, AssetSummary } from "../types/assets";
import { emptyAssetFilters } from "./useAssetFilters";

const EMPTY_SUMMARY: AssetListSummary = {
  total_assets: 0,
  online: 0,
  degraded: 0,
  offline: 0,
  maintenance_due: 0,
};

export function useAssets(filters: AssetFilters) {
  const [items, setItems] = useState<AssetSummary[]>([]);
  const [summary, setSummary] = useState<AssetListSummary>(EMPTY_SUMMARY);
  const [lastSeen, setLastSeen] = useState<string | null>(null);
  const [zones, setZones] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [filtered, all] = await Promise.all([
        fetchAssets(filters),
        fetchAssets(emptyAssetFilters()),
      ]);
      setItems(filtered.items);
      setTotal(filtered.total);
      setSummary(all.summary);
      setZones(uniqueAssetZones(all.items.map((item) => item.zone)));
      const latest = all.items
        .map((item) => item.last_seen_at)
        .filter((value): value is string => Boolean(value))
        .sort()
        .at(-1);
      setLastSeen(latest ?? null);
    } catch {
      setItems([]);
      setTotal(0);
      setSummary(EMPTY_SUMMARY);
      setZones([]);
      setLastSeen(null);
      setError(
        "We could not load assets from the AquaPulse service. Confirm the API is running, then try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  return { items, total, summary, zones, lastSeen, loading, error, reload: () => void load() };
}
