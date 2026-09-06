import { CLASSIFICATION_LABELS, SEVERITY_LABELS } from "../../lib/incidents";
import { scorePercent } from "../../lib/detections";
import type { DetectionDetail, PromotePayload } from "../../types/detections";
import type { IncidentClassification, SeverityTier } from "../../types/incidents";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";

export function PromoteDialog({
  open,
  busy,
  detection,
  title,
  severity,
  classification,
  summary,
  note,
  confirmed,
  onTitle,
  onSeverity,
  onClassification,
  onSummary,
  onNote,
  onConfirmed,
  onClose,
  onConfirm,
}: {
  open: boolean;
  busy: boolean;
  detection: DetectionDetail;
  title: string;
  severity: SeverityTier;
  classification: IncidentClassification;
  summary: string;
  note: string;
  confirmed: boolean;
  onTitle: (value: string) => void;
  onSeverity: (value: SeverityTier) => void;
  onClassification: (value: IncidentClassification) => void;
  onSummary: (value: string) => void;
  onNote: (value: string) => void;
  onConfirmed: (value: boolean) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!open) {
    return null;
  }

  const canSubmit = Boolean(title.trim() && summary.trim() && confirmed);

  return (
    <Modal
      title="Promote to incident"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={busy || !canSubmit}>
            {busy ? "Promoting…" : "Create incident"}
          </Button>
        </>
      }
    >
      <p className="rounded-2xl bg-warning/10 px-3 py-2 text-sm text-ink">
        Promotion creates an operational incident. It does not confirm that a leak exists.
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs text-ink-muted">
        <div>
          Detection
          <p className="text-sm text-ink">{detection.detection_number}</p>
        </div>
        <div>
          Sensor
          <p className="text-sm text-ink">{detection.sensor_id}</p>
        </div>
        <div>
          Zone
          <p className="text-sm text-ink">{detection.zone}</p>
        </div>
        <div>
          Confidence
          <p className="text-sm text-ink">{scorePercent(detection.anomaly_score)}</p>
        </div>
      </dl>
      <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Incident title
        <input
          value={title}
          onChange={(event) => onTitle(event.target.value)}
          className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink"
        />
      </label>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Severity
          <select
            value={severity}
            onChange={(event) => onSeverity(event.target.value as SeverityTier)}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            {(Object.keys(SEVERITY_LABELS) as SeverityTier[]).map((value) => (
              <option key={value} value={value}>
                {SEVERITY_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Classification
          <select
            value={classification}
            onChange={(event) => onClassification(event.target.value as IncidentClassification)}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            {(Object.keys(CLASSIFICATION_LABELS) as IncidentClassification[]).map((value) => (
              <option key={value} value={value}>
                {CLASSIFICATION_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Summary
        <textarea
          value={summary}
          onChange={(event) => onSummary(event.target.value)}
          rows={4}
          className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
        />
      </label>
      <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Operator note
        <textarea
          value={note}
          onChange={(event) => onNote(event.target.value)}
          rows={3}
          className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
        />
      </label>
      <label className="mt-4 flex items-start gap-2 text-sm text-ink">
        <input type="checkbox" className="mt-1" checked={confirmed} onChange={(event) => onConfirmed(event.target.checked)} />
        I understand this creates an incident and does not confirm a leak.
      </label>
    </Modal>
  );
}

export function defaultPromoteTitle(detection: DetectionDetail): string {
  return `Investigation of ${detection.detection_number} in ${detection.zone}`;
}

export function defaultPromoteSummary(detection: DetectionDetail): string {
  return `Promoted after manual review of ${detection.detection_number}. ${detection.trigger_reason}`;
}

export function defaultPromotePayload(detection: DetectionDetail): Pick<
  PromotePayload,
  "title" | "severity" | "classification" | "summary"
> {
  return {
    title: defaultPromoteTitle(detection),
    severity: "tier_2",
    classification: "suspected_leak",
    summary: defaultPromoteSummary(detection),
  };
}
