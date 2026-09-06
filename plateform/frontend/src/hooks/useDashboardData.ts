import { isAxiosError } from "axios";
import { useCallback, useRef, useState } from "react";

import { fetchDashboardSummary, fetchDashboardTelemetry } from "../api/dashboard";
import { usePolling } from "./usePolling";
import type { DashboardSummary, TelemetryReading, TelemetryResponse } from "../types/api";
import type { TelemetryRange } from "../types/telemetry";

const POLL_MS = 20_000;

interface DashboardDataState {
  summary: DashboardSummary | null;
  telemetry: TelemetryReading[];
  telemetryMeta: TelemetryResponse | null;
  range: TelemetryRange;
  setRange: (range: TelemetryRange) => void;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  backgroundError: string | null;
  lastRefreshAt: string | null;
  reload: () => void;
}

export function useDashboardData(): DashboardDataState {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [telemetryMeta, setTelemetryMeta] = useState<TelemetryResponse | null>(null);
  const [range, setRange] = useState<TelemetryRange>("1h");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backgroundError, setBackgroundError] = useState<string | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);
  const hasDataRef = useRef(false);
  hasDataRef.current = summary !== null;

  const load = useCallback(
    async (signal: AbortSignal) => {
      const hasData = hasDataRef.current;
      if (hasData) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      try {
        const [summaryData, telemetryData] = await Promise.all([
          fetchDashboardSummary({ signal }),
          fetchDashboardTelemetry(range, { signal }),
        ]);
        setSummary(summaryData);
        setTelemetry(telemetryData.readings);
        setTelemetryMeta(telemetryData);
        setError(null);
        setBackgroundError(null);
        setLastRefreshAt(new Date().toISOString());
      } catch (caught: unknown) {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") {
          return;
        }
        const message =
          "We could not load simulated telemetry. Confirm the API and database are running, then try again.";
        if (hasData) {
          setBackgroundError(message);
        } else {
          setError(message);
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [range],
  );

  usePolling({
    enabled: true,
    intervalMs: POLL_MS,
    resetKey: range,
    onTick: load,
  });

  return {
    summary,
    telemetry,
    telemetryMeta,
    range,
    setRange,
    loading,
    refreshing,
    error,
    backgroundError,
    lastRefreshAt,
    reload: () => {
      const controller = new AbortController();
      void load(controller.signal);
    },
  };
}
