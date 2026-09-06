import { isAxiosError } from "axios";
import { useCallback, useEffect, useState } from "react";

import { fetchAgentAuditRun } from "../api/agentAudit";
import { readApiError } from "../lib/apiError";
import type { AgentAuditRunDetail } from "../types/agentAudit";

export function useAgentAuditRun(runId: string | undefined) {
  const [run, setRun] = useState<AgentAuditRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    if (!runId) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const detail = await fetchAgentAuditRun(runId);
      setRun(detail);
      setError(null);
      setNotFound(false);
    } catch (caught: unknown) {
      if (isAxiosError(caught) && caught.response?.status === 404) {
        setRun(null);
        setNotFound(true);
        setError(readApiError(caught).message);
        return;
      }
      setRun(null);
      setNotFound(false);
      setError("We could not load this mock agent run.");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { run, loading, error, notFound, reload: load };
}
