import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { AgentAuditFilters } from "../types/agentAudit";

const EMPTY: AgentAuditFilters = {
  agent_code: "",
  status: "",
  decision: "",
  incident: "",
  detection: "",
  device: "",
  search: "",
};

export function useAgentAuditFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo<AgentAuditFilters>(
    () => ({
      agent_code: searchParams.get("agent") ?? "",
      status: searchParams.get("status") ?? "",
      decision: searchParams.get("decision") ?? "",
      incident: searchParams.get("incident") ?? "",
      detection: searchParams.get("detection") ?? "",
      device: searchParams.get("device") ?? "",
      search: searchParams.get("q") ?? "",
    }),
    [searchParams],
  );

  const replaceParams = useCallback(
    (next: AgentAuditFilters) => {
      const params = new URLSearchParams();
      if (next.agent_code.trim()) params.set("agent", next.agent_code.trim());
      if (next.status.trim()) params.set("status", next.status.trim());
      if (next.decision.trim()) params.set("decision", next.decision.trim());
      if (next.incident.trim()) params.set("incident", next.incident.trim());
      if (next.detection.trim()) params.set("detection", next.detection.trim());
      if (next.device.trim()) params.set("device", next.device.trim());
      if (next.search.trim()) params.set("q", next.search.trim());
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<AgentAuditFilters>) => replaceParams({ ...filters, ...patch }),
    [filters, replaceParams],
  );

  return {
    filters,
    setFilters,
    clearFilters: () => replaceParams(EMPTY),
    hasActiveFilters: Object.values(filters).some((value) => value.trim()),
  };
}
