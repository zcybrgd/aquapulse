import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchAnalyticsBundle } from "../api/analytics";
import type { AnalyticsBundle, AnalyticsFilters } from "../types/analytics";

export function useAnalyticsData(filters: AnalyticsFilters) {
  const [data, setData] = useState<AnalyticsBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const requestId = useRef(0);
  const filterKey = `${filters.range}|${filters.zone}|${filters.sensor}`;
  const lastFilterKey = useRef(filterKey);

  const reload = useCallback(() => {
    setRefreshNonce((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const current = requestId.current + 1;
    requestId.current = current;
    const filtersChanged = lastFilterKey.current !== filterKey;
    lastFilterKey.current = filterKey;
    if (filtersChanged) {
      setData(null);
      setLoading(true);
    } else if (data !== null) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    void fetchAnalyticsBundle(filters, { signal: controller.signal })
      .then((bundle) => {
        if (requestId.current !== current) {
          return;
        }
        setData(bundle);
        setError(null);
        setUpdatedAt(new Date());
      })
      .catch((caught: unknown) => {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") {
          return;
        }
        if (requestId.current !== current) {
          return;
        }
        setData(null);
        setError("We could not load analytics. Confirm the API and database are running, then try again.");
      })
      .finally(() => {
        if (requestId.current === current) {
          setLoading(false);
          setRefreshing(false);
        }
      });

    return () => {
      controller.abort();
    };
    // data is intentionally omitted so filter changes refetch instead of comparing stale bundles.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey, refreshNonce]);

  return { data, loading, refreshing, error, updatedAt, reload };
}
