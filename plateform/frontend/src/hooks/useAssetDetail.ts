import axios, { isAxiosError } from "axios";
import { useCallback, useRef, useState } from "react";

import { fetchAsset, fetchAssetHealth } from "../api/assets";
import type { AssetDetail, AssetHealthResponse } from "../types/assets";
import type { TelemetryRange } from "../types/telemetry";
import { usePolling } from "./usePolling";

const POLL_MS = 20_000;

export function useAssetDetail(assetId: string | undefined) {
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [health, setHealth] = useState<AssetHealthResponse | null>(null);
  const [range, setRange] = useState<TelemetryRange>("24h");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backgroundError, setBackgroundError] = useState<string | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);
  const hasDataRef = useRef(false);
  hasDataRef.current = asset !== null;

  const load = useCallback(
    async (signal: AbortSignal) => {
      if (!assetId) {
        setAsset(null);
        setHealth(null);
        setNotFound(true);
        setLoading(false);
        return;
      }

      const hasData = hasDataRef.current;
      if (hasData) {
        setRefreshing(true);
      } else {
        setLoading(true);
        setNotFound(false);
      }

      try {
        const [detail, healthData] = await Promise.all([
          fetchAsset(assetId),
          fetchAssetHealth(assetId, range, { signal }),
        ]);
        setAsset(detail);
        setHealth(healthData);
        setError(null);
        setBackgroundError(null);
        setNotFound(false);
        setLastRefreshAt(new Date().toISOString());
      } catch (caught) {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") {
          return;
        }
        if (axios.isAxiosError(caught) && caught.response?.status === 404) {
          setNotFound(true);
          setError(null);
          setAsset(null);
          setHealth(null);
        } else if (hasData) {
          setBackgroundError(
            "We could not refresh this asset. Previous values are still shown.",
          );
        } else {
          setNotFound(false);
          setError("We could not load this asset. Confirm the API is running, then try again.");
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [assetId, range],
  );

  usePolling({
    enabled: Boolean(assetId),
    intervalMs: POLL_MS,
    resetKey: `${assetId ?? ""}:${range}`,
    onTick: load,
  });

  return {
    asset,
    health,
    range,
    setRange,
    loading,
    refreshing,
    notFound,
    error,
    backgroundError,
    lastRefreshAt,
    reload: () => {
      const controller = new AbortController();
      void load(controller.signal);
    },
  };
}
