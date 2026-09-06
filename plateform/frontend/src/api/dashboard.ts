import { apiClient } from "./client";
import type { DashboardSummary, TelemetryResponse } from "../types/api";
import type { TelemetryRange } from "../types/telemetry";

export async function fetchDashboardSummary(
  config: { signal?: AbortSignal } = {},
): Promise<DashboardSummary> {
  const { data } = await apiClient.get<DashboardSummary>("/api/dashboard/summary", {
    signal: config.signal,
  });
  return data;
}

export async function fetchDashboardTelemetry(
  range: TelemetryRange = "1h",
  config: { signal?: AbortSignal } = {},
): Promise<TelemetryResponse> {
  const { data } = await apiClient.get<TelemetryResponse>("/api/dashboard/telemetry", {
    params: { range },
    signal: config.signal,
  });
  return data;
}
