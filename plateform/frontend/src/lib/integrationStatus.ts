import type { AgentRuntimeStatus } from "../types/integrations";

export function connectivityLabel(agent: AgentRuntimeStatus): string {
  if (agent.health_status === "not_configured" || !agent.configured) {
    return "Not configured";
  }
  if (agent.health_status === "unavailable" || !agent.reachable) {
    return "Unavailable";
  }
  if (agent.contract_status === "incompatible") {
    return "Contract mismatch";
  }
  if (agent.execution_enabled) {
    return "Connected and enabled";
  }
  return "Connected — execution disabled";
}

export function connectivityTone(agent: AgentRuntimeStatus): "success" | "critical" | "warning" | "muted" {
  const label = connectivityLabel(agent);
  if (label === "Not configured") return "muted";
  if (label === "Unavailable") return "critical";
  if (label === "Contract mismatch") return "warning";
  return "success";
}

export function executionLabel(agent: AgentRuntimeStatus): string {
  return agent.execution_enabled ? "Execution enabled" : "Execution disabled";
}

export function contractLabel(agent: AgentRuntimeStatus): string {
  if (agent.agent_type === "network_management_agent") {
    return "Unknown — awaiting confirmation";
  }
  if (agent.contract_status === "compatible") return "Compatible";
  if (agent.contract_status === "incompatible") return "Incompatible";
  if (agent.contract_status === "unavailable") return "Unavailable";
  return "Unknown";
}

export const CONNECTIVITY_BADGE_CLASS: Record<ReturnType<typeof connectivityTone>, string> = {
  success: "bg-success/15 text-success",
  critical: "bg-critical/10 text-critical",
  warning: "bg-warning/15 text-warning",
  muted: "bg-page text-ink-muted",
};

export const EXECUTION_BADGE_CLASS = {
  enabled: "bg-success/15 text-success",
  disabled: "bg-teal-light text-ink-muted",
} as const;
