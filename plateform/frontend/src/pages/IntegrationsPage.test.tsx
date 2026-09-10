import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useIntegrationReadiness } from "../hooks/useIntegrationReadiness";
import { useIntegrationStatus } from "../hooks/useIntegrationStatus";
import type { AgentRuntimeStatus, IntegrationBundle, IntegrationStatus } from "../types/integrations";
import { IntegrationsPage } from "./IntegrationsPage";

vi.mock("../hooks/useIntegrationReadiness", () => ({
  useIntegrationReadiness: vi.fn(),
}));
vi.mock("../hooks/useIntegrationStatus", () => ({
  useIntegrationStatus: vi.fn(),
}));

const mockedReadiness = vi.mocked(useIntegrationReadiness);
const mockedStatus = vi.mocked(useIntegrationStatus);

function runtime(overrides: Partial<AgentRuntimeStatus> = {}): AgentRuntimeStatus {
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

const emptyBundle: IntegrationBundle = {
  readiness: {
    prepared: true,
    execution_enabled: false,
    banner: "Integration prepared — agent execution disabled",
    advisory_notice: "Agent result is advisory",
    actuation_notice: "No physical command can be executed",
    safety: {
      camara_enabled: false,
      notifications_enabled: false,
      physical_commands_enabled: false,
      agent_execution_enabled: false,
      result_ingest_enabled: true,
    },
    agents: [],
    mapping_coverage: { enabled_mappings: 0, unmapped_findings: 0 },
    last_runs: [],
    contract_docs: {},
  },
  findings: [],
  recommendations: [],
};

function mockReady(status: IntegrationStatus, reload = vi.fn(), reloadStatus = vi.fn()) {
  mockedReadiness.mockReturnValue({
    data: emptyBundle,
    loading: false,
    error: null,
    reload,
  });
  mockedStatus.mockReturnValue({
    data: status,
    loading: false,
    refreshing: false,
    error: null,
    reload: reloadStatus,
  });
  return { reload, reloadStatus };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <IntegrationsPage />
    </MemoryRouter>,
  );
}

describe("IntegrationsPage status cards", () => {
  it("shows connected with execution disabled", () => {
    mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: false,
      agents: [runtime()],
    });
    renderPage();
    expect(screen.getByText("Connected — execution disabled")).toBeInTheDocument();
    expect(screen.getByText("Execution disabled")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Agent services may be connected for readiness checks, but AquaPulse agent execution remains disabled.",
      ),
    ).toBeInTheDocument();
  });

  it("shows connected and enabled", () => {
    mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: true,
      agents: [runtime({ execution_enabled: true })],
    });
    renderPage();
    expect(screen.getByText("Connected and enabled")).toBeInTheDocument();
    expect(screen.getByText("Execution enabled")).toBeInTheDocument();
    expect(
      screen.queryByText(
        "Agent services may be connected for readiness checks, but AquaPulse agent execution remains disabled.",
      ),
    ).not.toBeInTheDocument();
  });

  it("shows unavailable with a safe error", () => {
    mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: false,
      agents: [
        runtime({
          reachable: false,
          health_status: "unavailable",
          contract_status: "unavailable",
          error_code: "agent_unreachable",
          error_message: "Agent did not respond.",
        }),
      ],
    });
    renderPage();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.getByText("Agent did not respond.")).toBeInTheDocument();
  });

  it("shows not configured", () => {
    mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: false,
      agents: [
        runtime({
          configured: false,
          reachable: false,
          health_status: "not_configured",
          contract_status: "unknown",
          contract_version: null,
          response_time_ms: null,
          error_code: "agent_not_configured",
          error_message: "Agent URL is not configured.",
        }),
      ],
    });
    renderPage();
    expect(screen.getByText("Not configured")).toBeInTheDocument();
  });

  it("shows contract mismatch", () => {
    mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: false,
      agents: [
        runtime({
          contract_status: "incompatible",
          contract_version: "2.0",
          error_code: "agent_contract_mismatch",
          error_message: "Agent contract version is incompatible.",
        }),
      ],
    });
    renderPage();
    expect(screen.getByText("Contract mismatch")).toBeInTheDocument();
  });

  it("shows network contract unknown", () => {
    mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: false,
      agents: [
        runtime({
          agent_type: "network_management_agent",
          display_name: "Network Agent",
          contract_status: "unknown",
        }),
      ],
    });
    renderPage();
    expect(screen.getByText("Network Agent")).toBeInTheDocument();
    expect(screen.getByText("Unknown — awaiting confirmation")).toBeInTheDocument();
  });

  it("refreshes status from the existing Refresh button", async () => {
    const user = userEvent.setup();
    const { reload, reloadStatus } = mockReady({
      generated_at: "2026-09-10T10:00:00Z",
      execution_globally_enabled: false,
      agents: [runtime()],
    });
    renderPage();
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(reload).toHaveBeenCalledTimes(1);
    expect(reloadStatus).toHaveBeenCalledTimes(1);
  });

  it("shows a backend error state", () => {
    mockedReadiness.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      reload: vi.fn(),
    });
    mockedStatus.mockReturnValue({
      data: null,
      loading: false,
      refreshing: false,
      error: "Agent status could not be loaded.",
      reload: vi.fn(),
    });
    renderPage();
    expect(screen.getByText("Unable to load live data")).toBeInTheDocument();
    expect(screen.getByText("Agent status could not be loaded.")).toBeInTheDocument();
  });
});
