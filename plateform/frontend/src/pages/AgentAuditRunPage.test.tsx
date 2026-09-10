import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AgentAuditRunPage } from "./AgentAuditRunPage";

vi.mock("../hooks/useAgentAuditRun", () => ({
  useAgentAuditRun: vi.fn(),
}));

import { useAgentAuditRun } from "../hooks/useAgentAuditRun";

const mockedHook = vi.mocked(useAgentAuditRun);

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/agent-audit/runs/AGRUN-000001"]}>
      <Routes>
        <Route path="/agent-audit/runs/:runId" element={<AgentAuditRunPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AgentAuditRunPage", () => {
  it("shows an API error with retry", () => {
    mockedHook.mockReturnValue({
      data: null,
      run: null,
      loading: false,
      error: "We could not load this agent run. Confirm the API and database are running, then try again.",
      notFound: false,
      reload: vi.fn(),
    });
    renderPage();
    expect(screen.getByText("Unable to load agent run")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("keeps the back link on the Agent Audit trail", () => {
    mockedHook.mockReturnValue({
      data: null,
      run: null,
      loading: false,
      error: null,
      notFound: true,
      reload: vi.fn(),
    });
    renderPage();
    expect(screen.getByText("Agent run not found")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Back to Agent Audit Trail" })[0]).toHaveAttribute("href", "/agent-audit");
    expect(screen.queryByText("Back to Investigation Queue")).not.toBeInTheDocument();
  });
});
