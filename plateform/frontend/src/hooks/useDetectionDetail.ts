import axios from "axios";
import { useCallback, useEffect, useState } from "react";

import { fetchDetection, fetchDetectionAgentInput, fetchDetectionHistory } from "../api/detections";
import { fetchSensorTelemetry } from "../api/telemetry";
import type { DetectionDetail, InvestigationAgentInputV1, InvestigationEventItem } from "../types/detections";
import type { TelemetryHistoryResponse } from "../types/telemetry";

interface DetectionDetailState {
  detection: DetectionDetail | null;
  agentInput: InvestigationAgentInputV1 | null;
  history: TelemetryHistoryResponse | null;
  events: InvestigationEventItem[];
  loading: boolean;
  notFound: boolean;
  error: string | null;
  reload: () => void;
  setDetection: (detection: DetectionDetail) => void;
  refreshInvestigation: () => Promise<void>;
}

export function useDetectionDetail(detectionId: string | undefined): DetectionDetailState {
  const [detection, setDetection] = useState<DetectionDetail | null>(null);
  const [agentInput, setAgentInput] = useState<InvestigationAgentInputV1 | null>(null);
  const [history, setHistory] = useState<TelemetryHistoryResponse | null>(null);
  const [events, setEvents] = useState<InvestigationEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!detectionId) {
      setDetection(null);
      setAgentInput(null);
      setHistory(null);
      setEvents([]);
      setNotFound(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const [detail, agent, investigation] = await Promise.all([
        fetchDetection(detectionId),
        fetchDetectionAgentInput(detectionId),
        fetchDetectionHistory(detectionId),
      ]);
      setDetection(detail);
      setAgentInput(agent);
      setEvents(investigation.events);
      const paddedStart = new Date(new Date(detail.window_start).getTime() - 15 * 60_000).toISOString();
      const paddedEnd = new Date(new Date(detail.window_end).getTime() + 15 * 60_000).toISOString();
      try {
        const series = await fetchSensorTelemetry(detail.sensor_id, {
          start: paddedStart,
          end: paddedEnd,
          interval: "raw",
          metrics: ["pressure", "flow", "signal", "packet_loss"],
        });
        setHistory(series);
      } catch {
        setHistory(null);
      }
    } catch (caught) {
      setDetection(null);
      setAgentInput(null);
      setHistory(null);
      setEvents([]);
      if (axios.isAxiosError(caught) && caught.response?.status === 404) {
        setNotFound(true);
        setError(null);
      } else {
        setNotFound(false);
        setError("We could not load this detection. Confirm the API is running, then try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [detectionId]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    detection,
    agentInput,
    history,
    events,
    loading,
    notFound,
    error,
    reload: () => void load(),
    setDetection,
    refreshInvestigation: async () => {
      if (!detectionId) {
        return;
      }
      const [detail, investigation] = await Promise.all([
        fetchDetection(detectionId),
        fetchDetectionHistory(detectionId),
      ]);
      setDetection(detail);
      setEvents(investigation.events);
    },
  };
}
