import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useAgentAuditData } from "../hooks/useAgentAuditData";
import type { AgentAuditSummary } from "../types/agentAudit";
import { AgentAuditPage } from "./AgentAuditPage";

vi.mock("../hooks/useAgentAuditData", () => ({
  useAgentAuditData: vi.fn(),
}));

const mocked = vi.mocked(useAgentAuditData);

describe("AgentAuditPage empty state", () => {
  it("does not show zero-run summary cards", () => {
    mocked.mockReturnValue({
      summary: {
        total_runs: 0,
        successful_runs: 0,
        failed_runs: 0,
        blocked_actions: 0,
        average_duration_ms: null,
        runs_by_agent: [],
        stages_reached: [],
        last_run_at: null,
        unmapped_identity_count: 0,
        data_mode: "ingested",
        reference_time: "2026-09-10T00:00:00Z",
        note: "",
      } satisfies AgentAuditSummary,
      runs: {
        items: [],
        total: 0,
        page: 1,
        page_size: 25,
        data_mode: "ingested",
        reference_time: "2026-09-10T00:00:00Z",
      },
      loading: false,
      refreshing: false,
      error: null,
      updatedAt: null,
      reload: vi.fn(),
    });
    render(
      <MemoryRouter>
        <AgentAuditPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("No agent runs yet")).toBeInTheDocument();
    expect(
      screen.getByText("Runs will appear after an external agent is connected and executed."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Total runs")).not.toBeInTheDocument();
  });
});
