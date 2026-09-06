import { useCallback, useEffect, useState } from "react";

import { fetchIncidentMaintenance } from "../api/maintenance";
import type { IncidentMaintenanceResponse } from "../types/maintenance";

export function useIncidentMaintenance(incidentId: string | undefined) {
  const [data, setData] = useState<IncidentMaintenanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!incidentId) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await fetchIncidentMaintenance(incidentId));
    } catch {
      setError("Related maintenance could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, loading, error };
}
