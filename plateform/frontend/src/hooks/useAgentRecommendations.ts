import { useCallback, useEffect, useState } from "react";

import { fetchAgentRecommendations } from "../api/integrations";
import type { AgentRecommendationRecord } from "../types/integrations";

const MOCK_MODE = "mock_agent_data";

export function useAgentRecommendations() {
  const [items, setItems] = useState<AgentRecommendationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const recommendations = await fetchAgentRecommendations({ signal });
      setItems(recommendations.filter((item) => item.data_mode !== MOCK_MODE));
    } catch {
      setItems([]);
      setError("We could not load Response Agent recommendations. Confirm the API is running, then try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { items, loading, error, reload: () => void load() };
}
