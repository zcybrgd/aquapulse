import { describe, expect, it } from "vitest";

import { connectivityLabel, contractLabel, executionLabel } from "./integrationStatus";
import type { AgentRuntimeStatus } from "../types/integrations";

function agent(overrides: Partial<AgentRuntimeStatus> = {}): AgentRuntimeStatus {
  return {
    agent_type: "investigation_agent",
    display_name: "Investigation Agent",
    configured: true,
    execution_enabled: false,
    reachable: true,
    health_status: "healthy",
    contract_status: "compatible",
    contract_version: "1.0",
    checked_at: "2026-09-10T10:00:00Z",
    response_time_ms: 24,
    error_code: null,
    error_message: null,
    ...overrides,
  };
}

describe("integration status labels", () => {
  it("shows connected with execution disabled", () => {
    expect(connectivityLabel(agent())).toBe("Connected — execution disabled");
    expect(executionLabel(agent())).toBe("Execution disabled");
  });

  it("shows connected and enabled", () => {
    const enabled = agent({ execution_enabled: true });
    expect(connectivityLabel(enabled)).toBe("Connected and enabled");
    expect(executionLabel(enabled)).toBe("Execution enabled");
  });

  it("shows unavailable", () => {
    expect(
      connectivityLabel(
        agent({
          reachable: false,
          health_status: "unavailable",
          error_code: "agent_unreachable",
          error_message: "Agent did not respond.",
        }),
      ),
    ).toBe("Unavailable");
  });

  it("shows not configured", () => {
    expect(
      connectivityLabel(
        agent({
          configured: false,
          reachable: false,
          health_status: "not_configured",
          contract_status: "unknown",
          contract_version: null,
          response_time_ms: null,
          error_code: "agent_not_configured",
          error_message: "Agent URL is not configured.",
        }),
      ),
    ).toBe("Not configured");
  });

  it("shows contract mismatch", () => {
    expect(
      connectivityLabel(
        agent({
          contract_status: "incompatible",
          contract_version: "2.0",
          error_code: "agent_contract_mismatch",
          error_message: "Agent contract version is incompatible.",
        }),
      ),
    ).toBe("Contract mismatch");
  });

  it("keeps the network contract unknown", () => {
    expect(
      contractLabel(
        agent({
          agent_type: "network_management_agent",
          display_name: "Network Agent",
          contract_status: "unknown",
          contract_version: "1.0",
        }),
      ),
    ).toBe("Unknown — awaiting confirmation");
  });
});
