import { useCallback, useEffect, useState } from "react";

import { fetchAgentFindings } from "../api/integrations";
import type { AgentFindingRecord } from "../types/integrations";

const MOCK_MODE = "mock_agent_data";

export function useAgentFindings() {
  const [items, setItems] = useState<AgentFindingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const findings = await fetchAgentFindings();
      setItems(findings.filter((item) => item.data_mode !== MOCK_MODE));
    } catch {
      setItems([]);
      setError("We could not load Investigation Agent results. Confirm the API is running, then try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { items, loading, error, reload: () => void load() };
}
