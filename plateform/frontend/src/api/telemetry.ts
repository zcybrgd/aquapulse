import { apiClient } from "./client";
import type {
  LatestTelemetryBatch,
  LatestTelemetryResponse,
  NetworkTelemetrySummary,
  TelemetryHistoryResponse,
  TelemetryInterval,
  TelemetryMetric,
  TelemetryRange,
} from "../types/telemetry";

export async function fetchSensorTelemetry(
  sensorId: string,
  params: {
    range?: TelemetryRange;
    start?: string;
    end?: string;
    interval?: TelemetryInterval;
    metrics?: TelemetryMetric[];
    limit?: number;
  } = {},
  config: { signal?: AbortSignal } = {},
): Promise<TelemetryHistoryResponse> {
  const query: Record<string, string | number> = {};
  if (params.range) {
    query.range = params.range;
  }
  if (params.start) {
    query.start = params.start;
  }
  if (params.end) {
    query.end = params.end;
  }
  if (params.interval) {
    query.interval = params.interval;
  }
  if (params.metrics && params.metrics.length > 0) {
    query.metrics = params.metrics.join(",");
  }
  if (params.limit) {
    query.limit = params.limit;
  }
  const { data } = await apiClient.get<TelemetryHistoryResponse>(
    `/api/telemetry/sensors/${encodeURIComponent(sensorId)}`,
    { params: query, signal: config.signal },
  );
  return data;
}

export async function fetchSensorLatest(
  sensorId: string,
  config: { signal?: AbortSignal } = {},
): Promise<LatestTelemetryResponse> {
  const { data } = await apiClient.get<LatestTelemetryResponse>(
    `/api/telemetry/sensors/${encodeURIComponent(sensorId)}/latest`,
    { signal: config.signal },
  );
  return data;
}

export async function fetchLatestTelemetryBatch(
  config: { signal?: AbortSignal } = {},
): Promise<LatestTelemetryBatch> {
  const { data } = await apiClient.get<LatestTelemetryBatch>("/api/telemetry/sensors/latest", {
    signal: config.signal,
  });
  return data;
}

export async function fetchNetworkTelemetrySummary(
  config: { signal?: AbortSignal } = {},
): Promise<NetworkTelemetrySummary> {
  const { data } = await apiClient.get<NetworkTelemetrySummary>("/api/telemetry/network/summary", {
    signal: config.signal,
  });
  return data;
}
