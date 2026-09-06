import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchAgentAuditRuns, fetchAgentAuditSummary } from "../api/agentAudit";
import type { AgentAuditFilters, AgentAuditRunListResponse, AgentAuditSummary } from "../types/agentAudit";

export function useAgentAuditData(filters: AgentAuditFilters) {
  const [summary, setSummary] = useState<AgentAuditSummary | null>(null);
  const [runs, setRuns] = useState<AgentAuditRunListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const requestId = useRef(0);
  const filterKey = JSON.stringify(filters);
  const lastFilterKey = useRef(filterKey);

  const reload = useCallback(() => setRefreshNonce((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const current = requestId.current + 1;
    requestId.current = current;
    const changed = lastFilterKey.current !== filterKey;
    lastFilterKey.current = filterKey;
    if (changed || summary === null) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    void Promise.all([
      fetchAgentAuditSummary(filters, { signal: controller.signal }),
      fetchAgentAuditRuns(filters, { signal: controller.signal }),
    ])
      .then(([nextSummary, nextRuns]) => {
        if (requestId.current !== current) return;
        setSummary(nextSummary);
        setRuns(nextRuns);
        setError(null);
        setUpdatedAt(new Date());
      })
      .catch((caught: unknown) => {
        if (isAxiosError(caught) && caught.code === "ERR_CANCELED") return;
        if (requestId.current !== current) return;
        setSummary(null);
        setRuns(null);
        setError("We could not load the mock agent audit trail. Confirm the API and database are running, then try again.");
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

  return { summary, runs, loading, refreshing, error, updatedAt, reload };
}
