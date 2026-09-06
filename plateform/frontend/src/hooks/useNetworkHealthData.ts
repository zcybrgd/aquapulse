import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchNetworkEvents, fetchNetworkSummary } from "../api/networkHealth";
import type { NetworkEventListResponse, NetworkFilters, NetworkSummary } from "../types/networkHealth";

export function useNetworkHealthData(filters: NetworkFilters) {
  const [summary, setSummary] = useState<NetworkSummary | null>(null);
  const [events, setEvents] = useState<NetworkEventListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const requestId = useRef(0);
  const filterKey = JSON.stringify(filters);

  const reload = useCallback(() => setRefreshNonce((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const current = requestId.current + 1;
    requestId.current = current;
    setLoading(summary === null);
    setRefreshing(summary !== null);

    void Promise.all([
      fetchNetworkSummary(filters, { signal: controller.signal }),
      fetchNetworkEvents(filters, { signal: controller.signal }),
    ])
      .then(([nextSummary, nextEvents]) => {
        if (requestId.current !== current) return;
        setSummary(nextSummary);
        setEvents(nextEvents);
        setError(null);
        setUpdatedAt(new Date());
      })
      .catch((caught: unknown) => {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") return;
        if (requestId.current !== current) return;
        setSummary(null);
        setEvents(null);
        setError("We could not load mock Network Agent logs. Confirm the API and database are running.");
      })
      .finally(() => {
        if (requestId.current === current) {
          setLoading(false);
          setRefreshing(false);
        }
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey, refreshNonce]);

  return { summary, events, loading, refreshing, error, updatedAt, reload };
}
