import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchIntegrationStatus } from "../api/integrations";
import type { IntegrationStatus } from "../types/integrations";

const DEFAULT_POLL_MS = 20_000;

export function useIntegrationStatus(options?: { pollMs?: number }) {
  const pollMs = options?.pollMs ?? DEFAULT_POLL_MS;
  const [data, setData] = useState<IntegrationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const requestId = useRef(0);
  const hasData = useRef(false);

  const reload = useCallback(() => {
    setRefreshNonce((value) => value + 1);
  }, []);

  useEffect(() => {
    hasData.current = data !== null;
  }, [data]);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const controller = new AbortController();

    const load = (refresh: boolean) => {
      const current = requestId.current + 1;
      requestId.current = current;
      if (hasData.current) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      void fetchIntegrationStatus({ signal: controller.signal, refresh })
        .then((status) => {
          if (cancelled || requestId.current !== current) return;
          setData(status);
          setError(null);
        })
        .catch((caught: unknown) => {
          if (isAxiosError(caught) && caught.code === "ERR_CANCELED") return;
          if (cancelled || requestId.current !== current) return;
          if (!hasData.current) {
            setError("Agent status could not be loaded.");
          }
        })
        .finally(() => {
          if (cancelled || requestId.current !== current) return;
          setLoading(false);
          setRefreshing(false);
        });
    };

    const schedule = () => {
      window.clearInterval(timer);
      if (document.visibilityState !== "visible") return;
      timer = window.setInterval(() => {
        if (document.visibilityState === "visible") {
          load(false);
        }
      }, pollMs);
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        load(false);
        schedule();
      } else {
        window.clearInterval(timer);
      }
    };

    load(refreshNonce > 0);
    if (document.visibilityState === "visible") {
      schedule();
    }
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [pollMs, refreshNonce]);

  return { data, loading, refreshing, error, reload };
}
