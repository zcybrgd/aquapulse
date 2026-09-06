import axios from "axios";
import { useCallback, useEffect, useState } from "react";

import { fetchWorkOrder } from "../api/maintenance";
import type { WorkOrderDetail } from "../types/maintenance";

export function useWorkOrderDetail(workOrderId: string | undefined) {
  const [workOrder, setWorkOrder] = useState<WorkOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!workOrderId) {
      setWorkOrder(null);
      setNotFound(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      setWorkOrder(await fetchWorkOrder(workOrderId));
    } catch (caught) {
      setWorkOrder(null);
      if (axios.isAxiosError(caught) && caught.response?.status === 404) {
        setNotFound(true);
      } else {
        setError("We could not load this work order. Try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [workOrderId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { workOrder, loading, notFound, error, reload: load };
}
