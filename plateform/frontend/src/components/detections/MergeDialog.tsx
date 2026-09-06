import { useEffect, useMemo, useState } from "react";

import { fetchDetections } from "../../api/detections";
import { emptyDetectionFilters, RULE_LABELS, scorePercent } from "../../lib/detections";
import type { DetectionSummary } from "../../types/detections";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { DetectionPriorityBadge } from "./DetectionPriorityBadge";
import { DetectionStatusBadge } from "./DetectionStatusBadge";

export function MergeDialog({
  open,
  busy,
  currentId,
  selectedId,
  note,
  onSelect,
  onNote,
  onClose,
  onConfirm,
}: {
  open: boolean;
  busy: boolean;
  currentId: string;
  selectedId: string;
  note: string;
  onSelect: (value: string) => void;
  onNote: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<DetectionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void fetchDetections(emptyDetectionFilters())
      .then((response) => {
        if (!cancelled) {
          setItems(response.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setLoadError("Unable to load eligible detections.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const eligible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter((item) => {
      if (item.id === currentId) {
        return false;
      }
      if (item.status === "promoted" || item.status === "merged" || item.status === "dismissed") {
        return false;
      }
      if (!needle) {
        return true;
      }
      return [item.detection_number, item.rule_code, item.sensor_id, item.zone, item.status]
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [currentId, items, query]);

  if (!open) {
    return null;
  }

  return (
    <Modal
      title="Merge detection"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={busy || !selectedId}>
            {busy ? "Merging…" : "Confirm merge"}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ink-muted">
        The source becomes merged. The target stays active. Evidence records are not combined or deleted.
      </p>
      <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Search eligible detections
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
          placeholder="ID, rule, sensor or zone"
        />
      </label>
      <ul className="mt-3 max-h-56 space-y-2 overflow-y-auto">
        {loading ? (
          <li className="text-sm text-ink-muted">Loading eligible detections…</li>
        ) : loadError ? (
          <li className="text-sm text-critical">{loadError}</li>
        ) : eligible.length === 0 ? (
          <li className="text-sm text-ink-muted">No eligible active detections.</li>
        ) : (
          eligible.map((item) => (
            <li key={item.id}>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-2xl border p-3 ${
                  selectedId === item.id ? "border-teal" : "border-line"
                }`}
              >
                <input
                  type="radio"
                  name="merge-target"
                  className="mt-1"
                  checked={selectedId === item.id}
                  onChange={() => onSelect(item.id)}
                />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-ink">{item.detection_number}</span>
                    <DetectionPriorityBadge priority={item.priority} />
                    <DetectionStatusBadge status={item.status} />
                  </span>
                  <span className="mt-1 block text-xs text-ink-muted">
                    {RULE_LABELS[item.rule_code] ?? item.rule_name} · {item.sensor_id} · {item.zone} · score{" "}
                    {scorePercent(item.anomaly_score)}
                  </span>
                </span>
              </label>
            </li>
          ))
        )}
      </ul>
      <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Note
        <textarea
          value={note}
          onChange={(event) => onNote(event.target.value)}
          rows={3}
          className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
        />
      </label>
    </Modal>
  );
}
