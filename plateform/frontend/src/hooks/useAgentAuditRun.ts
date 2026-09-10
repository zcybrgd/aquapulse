import { isAxiosError } from "axios";
import { useCallback, useEffect, useRef, useState } from "react";

import { fetchAgentAuditRun } from "../api/agentAudit";
import { fetchAgentFindings, fetchAgentRecommendations, fetchAgentRun } from "../api/integrations";
import { readApiError } from "../lib/apiError";
import type { AgentAuditRunDetail } from "../types/agentAudit";
import type { AgentFindingRecord, AgentRecommendationRecord, AgentRunDetail } from "../types/integrations";

function isCanceled(caught: unknown): boolean {
  return isAxiosError(caught) && caught.code === "ERR_CANCELED";
}

export interface AgentAuditRunPageData {
  run: AgentAuditRunDetail;
  integration: AgentRunDetail | null;
  findings: AgentFindingRecord[];
  recommendations: AgentRecommendationRecord[];
}

export function useAgentAuditRun(runId: string | undefined) {
  const [data, setData] = useState<AgentAuditRunPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const requestId = useRef(0);

  const resolvedId = runId ? decodeURIComponent(runId) : "";

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const current = requestId.current + 1;
      requestId.current = current;
      if (!resolvedId) {
        setData(null);
        setNotFound(true);
        setError(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      setNotFound(false);
      try {
        const run = await fetchAgentAuditRun(resolvedId, { signal });
        const [integrationResult, findingsResult, recommendationsResult] = await Promise.allSettled([
          fetchAgentRun(run.public_id, { signal }),
          fetchAgentFindings({ signal }),
          fetchAgentRecommendations({ signal }),
        ]);
        if (requestId.current !== current) return;
        const integration = integrationResult.status === "fulfilled" ? integrationResult.value : null;
        const findings =
          findingsResult.status === "fulfilled"
            ? findingsResult.value.filter((item) => item.run_id === run.public_id)
            : [];
        const recommendations =
          recommendationsResult.status === "fulfilled"
            ? recommendationsResult.value.filter((item) => item.run_id === run.public_id)
            : [];
        setData({ run, integration, findings, recommendations });
        setError(null);
        setNotFound(false);
      } catch (caught: unknown) {
        if (isCanceled(caught) || requestId.current !== current) return;
        setData(null);
        if (isAxiosError(caught) && caught.response?.status === 404) {
          setNotFound(true);
          setError(readApiError(caught).message);
          return;
        }
        setNotFound(false);
        setError("We could not load this agent run. Confirm the API and database are running, then try again.");
      } finally {
        if (requestId.current === current) {
          setLoading(false);
        }
      }
    },
    [resolvedId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return {
    data,
    run: data?.run ?? null,
    loading,
    error,
    notFound,
    reload: () => void load(),
  };
}
