import { useCallback, useEffect, useState } from "react";

import { fetchDetections, fetchDetectionSummary } from "../api/detections";
import { emptyDetectionFilters } from "../lib/detections";
import type {
  DetectionFilters,
  DetectionQueueStats,
  DetectionSummary,
} from "../types/detections";

export function useDetections(filters: DetectionFilters) {
  const [items, setItems] = useState<DetectionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<DetectionQueueStats | null>(null);
  const [zones, setZones] = useState<string[]>([]);
  const [rules, setRules] = useState<string[]>([]);
  const [sensors, setSensors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [filtered, all, summary] = await Promise.all([
        fetchDetections(filters),
        fetchDetections(emptyDetectionFilters()),
        fetchDetectionSummary(),
      ]);
      setItems(filtered.items);
      setTotal(filtered.total);
      setStats(summary);
      setZones([...new Set(all.items.map((item) => item.zone).filter(Boolean))].sort());
      setRules([...new Set(all.items.map((item) => item.rule_code))].sort());
      setSensors([...new Set(all.items.map((item) => item.sensor_id))].sort());
    } catch {
      setItems([]);
      setTotal(0);
      setStats(null);
      setError(
        "We could not load detections from the AquaPulse service. Confirm the API is running, then try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  return { items, total, stats, zones, rules, sensors, loading, error, reload: () => void load() };
}

export function useDetectionPreview() {
  const [stats, setStats] = useState<DetectionQueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStats(await fetchDetectionSummary());
    } catch {
      setStats(null);
      setError("Detection preview is unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { stats, loading, error, reload: () => void load() };
}
