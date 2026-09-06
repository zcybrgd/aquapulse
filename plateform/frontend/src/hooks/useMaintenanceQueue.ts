import { useCallback, useEffect, useState } from "react";

import { fetchAssets } from "../api/assets";
import { fetchUpcomingMaintenance, fetchWorkOrders } from "../api/maintenance";
import { uniqueAssetZones } from "../lib/assets";
import type { MaintenanceFilters, UpcomingMaintenanceItem, WorkOrderListResponse } from "../types/maintenance";
import { emptyAssetFilters } from "./useAssetFilters";

export function useMaintenanceQueue(filters: MaintenanceFilters) {
  const [data, setData] = useState<WorkOrderListResponse | null>(null);
  const [upcoming, setUpcoming] = useState<UpcomingMaintenanceItem[]>([]);
  const [zones, setZones] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [payload, upcomingItems, assets] = await Promise.all([
        fetchWorkOrders(filters),
        fetchUpcomingMaintenance(),
        fetchAssets(emptyAssetFilters()),
      ]);
      setData(payload);
      setUpcoming(upcomingItems);
      setZones(uniqueAssetZones(assets.items.map((item) => item.zone)));
      setUpdatedAt(new Date());
    } catch {
      setError("We could not load the Maintenance Center. Confirm the API is running, then try again.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, upcoming, zones, loading, error, updatedAt, reload: () => void load() };
}
