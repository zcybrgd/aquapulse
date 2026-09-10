import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchIntegrationBundle } from "../api/integrations";
import type { IntegrationBundle } from "../types/integrations";

export function useIntegrationReadiness() {
  const [data, setData] = useState<IntegrationBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const requestId = useRef(0);
  const dataRef = useRef(data);
  dataRef.current = data;

  const reload = useCallback(() => {
    setRefreshNonce((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const current = requestId.current + 1;
    requestId.current = current;
    if (!dataRef.current) setLoading(true);

    void fetchIntegrationBundle({ signal: controller.signal })
      .then((bundle) => {
        if (requestId.current !== current) return;
        setData(bundle);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") return;
        if (requestId.current !== current) return;
        if (!dataRef.current) setError("Integration readiness could not be loaded.");
      })
      .finally(() => {
        if (requestId.current === current) setLoading(false);
      });

    return () => controller.abort();
  }, [refreshNonce]);

  return { data, loading, error, reload };
}
