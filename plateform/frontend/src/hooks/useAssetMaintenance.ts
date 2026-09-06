import { useCallback, useEffect, useState } from "react";

import { fetchAssetMaintenance } from "../api/maintenance";
import type { AssetMaintenanceResponse } from "../types/maintenance";

export function useAssetMaintenance(assetId: string | undefined) {
  const [data, setData] = useState<AssetMaintenanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!assetId) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await fetchAssetMaintenance(assetId));
    } catch {
      setError("Maintenance records could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, loading, error, reload: () => void load() };
}
