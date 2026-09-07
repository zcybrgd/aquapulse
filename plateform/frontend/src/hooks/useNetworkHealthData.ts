import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchNetworkDevices, fetchNetworkSummary, refreshNetworkDevices } from "../api/networkHealth";
import type { DeviceNetworkListResponse, DeviceNetworkSummary, NetworkFilters } from "../types/networkHealth";

export function useNetworkHealthData(filters: NetworkFilters) {
  const [summary, setSummary] = useState<DeviceNetworkSummary | null>(null);
  const [devices, setDevices] = useState<DeviceNetworkListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const requestId = useRef(0);
  const listFilters = {
    search: filters.search,
    zone: filters.zone,
    asset_type: filters.asset_type,
    reachability: filters.reachability,
    location_available: filters.location_available,
    cellular_available: filters.cellular_available,
    source_mode: filters.source_mode,
    device: "",
  };
  const filterKey = JSON.stringify(listFilters);

  const reload = useCallback(() => setRefreshNonce((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const current = requestId.current + 1;
    requestId.current = current;
    setLoading(summary === null);
    setRefreshing(summary !== null);

    void Promise.all([
      fetchNetworkSummary(listFilters, { signal: controller.signal }),
      fetchNetworkDevices(listFilters, { signal: controller.signal }),
    ])
      .then(([nextSummary, nextDevices]) => {
        if (requestId.current !== current) return;
        setSummary(nextSummary);
        setDevices(nextDevices);
        setError(null);
        setUpdatedAt(new Date());
      })
      .catch((caught: unknown) => {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") return;
        if (requestId.current !== current) return;
        setSummary(null);
        setDevices(null);
        setError("We could not load device network health. Confirm the API and database are running.");
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

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshNetworkDevices(false);
      reload();
    } catch {
      setError("Device network refresh did not complete. Try again shortly.");
      setRefreshing(false);
    }
  }, [reload]);

  return { summary, devices, loading, refreshing, error, updatedAt, reload, refreshAll };
}
