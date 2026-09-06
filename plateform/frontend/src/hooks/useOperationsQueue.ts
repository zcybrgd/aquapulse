import { useCallback, useEffect, useState } from "react";

import { fetchOperationsQueue } from "../api/operations";
import type { OperationsFilters, OperationsQueueResponse } from "../types/incidents";

export function useOperationsQueue(filters: OperationsFilters) {
  const [data, setData] = useState<OperationsQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchOperationsQueue(filters);
      setData(payload);
      setUpdatedAt(new Date());
    } catch {
      setError("We could not load the Operations Center. Confirm the API is running, then try again.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    data,
    loading,
    error,
    updatedAt,
    reload: () => void load(),
  };
}
