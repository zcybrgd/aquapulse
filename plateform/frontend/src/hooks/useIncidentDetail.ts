import axios from "axios";
import { useCallback, useEffect, useState } from "react";

import { fetchIncident, fetchIncidentTimeline } from "../api/incidents";
import type { IncidentDetail, IncidentTimelineEvent } from "../types/incidents";

interface IncidentDetailState {
  incident: IncidentDetail | null;
  events: IncidentTimelineEvent[];
  loading: boolean;
  notFound: boolean;
  error: string | null;
  reload: () => void;
}

export function useIncidentDetail(incidentId: string | undefined): IncidentDetailState {
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [events, setEvents] = useState<IncidentTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!incidentId) {
      setIncident(null);
      setEvents([]);
      setNotFound(true);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);

    try {
      const [detail, timeline] = await Promise.all([
        fetchIncident(incidentId),
        fetchIncidentTimeline(incidentId),
      ]);
      setIncident(detail);
      setEvents(timeline.events);
    } catch (caught) {
      setIncident(null);
      setEvents([]);
      if (axios.isAxiosError(caught) && caught.response?.status === 404) {
        setNotFound(true);
        setError(null);
      } else {
        setNotFound(false);
        setError(
          "We could not load this incident. Confirm the API is running, then try again.",
        );
      }
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { incident, events, loading, notFound, error, reload: () => void load() };
}
