import { useCallback, useEffect, useState } from "react";

import { fetchIncidentOperations } from "../api/operations";
import type { IncidentOperations } from "../types/incidents";

export function useIncidentOperations(incidentId: string | undefined) {
  const [operations, setOperations] = useState<IncidentOperations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!incidentId) {
      setOperations(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setOperations(await fetchIncidentOperations(incidentId));
    } catch {
      setError("Operational state could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { operations, loading, error, reload: () => void load(), setOperations };
}
