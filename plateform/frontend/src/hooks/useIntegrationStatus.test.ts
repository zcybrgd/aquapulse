import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchIntegrationStatus } from "../api/integrations";
import type { IntegrationStatus } from "../types/integrations";
import { useIntegrationStatus } from "./useIntegrationStatus";

vi.mock("../api/integrations", () => ({
  fetchIntegrationStatus: vi.fn(),
}));

const mockedFetch = vi.mocked(fetchIntegrationStatus);

function status(overrides: Partial<IntegrationStatus> = {}): IntegrationStatus {
  return {
    generated_at: "2026-09-10T10:00:00Z",
    execution_globally_enabled: false,
    agents: [
      {
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
      },
    ],
    ...overrides,
  };
}

describe("useIntegrationStatus", () => {
  beforeEach(() => {
    mockedFetch.mockReset();
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "visible",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps the previous result while a manual refresh is in flight", async () => {
    const first = status();
    let resolveSecond: (value: IntegrationStatus) => void = () => undefined;
    mockedFetch.mockResolvedValueOnce(first).mockImplementationOnce(
      () =>
        new Promise<IntegrationStatus>((resolve) => {
          resolveSecond = resolve;
        }),
    );

    const { result } = renderHook(() => useIntegrationStatus({ pollMs: 60_000 }));
    await waitFor(() => expect(result.current.data).toEqual(first));

    act(() => {
      result.current.reload();
    });
    await waitFor(() => expect(result.current.refreshing).toBe(true));
    expect(result.current.data).toEqual(first);
    expect(result.current.loading).toBe(false);

    await act(async () => {
      resolveSecond(status({ generated_at: "2026-09-10T10:01:00Z" }));
    });
    await waitFor(() => expect(result.current.refreshing).toBe(false));
    expect(result.current.data?.generated_at).toBe("2026-09-10T10:01:00Z");
  });

  it("polls only while the page is visible", async () => {
    vi.useFakeTimers();
    mockedFetch.mockResolvedValue(status());
    renderHook(() => useIntegrationStatus({ pollMs: 20_000 }));
    await act(async () => {
      await Promise.resolve();
    });
    expect(mockedFetch).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(20_000);
      await Promise.resolve();
    });
    expect(mockedFetch).toHaveBeenCalledTimes(2);

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "hidden",
    });
    document.dispatchEvent(new Event("visibilitychange"));

    await act(async () => {
      vi.advanceTimersByTime(40_000);
      await Promise.resolve();
    });
    expect(mockedFetch).toHaveBeenCalledTimes(2);
  });
});
