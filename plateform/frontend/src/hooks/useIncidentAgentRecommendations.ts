import { isAxiosError } from "axios";
import { useCallback, useEffect, useState } from "react";

import { fetchAgentAuditRuns } from "../api/agentAudit";
import type { AgentAuditRunSummary } from "../types/agentAudit";

export function useIncidentAgentRecommendations(incidentNumber: string | undefined) {
  const [runs, setRuns] = useState<AgentAuditRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!incidentNumber) {
      setRuns([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const result = await fetchAgentAuditRuns({
        agent_code: "",
        status: "",
        decision: "",
        incident: incidentNumber,
        detection: "",
        device: "",
        search: "",
      });
      // Only response_agent runs are relevant to this panel
      setRuns(result.items.filter((run) => run.agent_type === "response_agent"));
      setError(null);
    } catch (caught: unknown) {
      setRuns([]);
      if (!isAxiosError(caught)) {
        setError("We could not load agent recommendations for this incident.");
      }
    } finally {
      setLoading(false);
    }
  }, [incidentNumber]);

  useEffect(() => {
    void load();
  }, [load]);

  return { runs, loading, error, reload: load };
}