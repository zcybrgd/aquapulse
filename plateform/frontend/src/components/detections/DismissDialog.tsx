import { DISMISSAL_LABELS } from "../../lib/detections";
import type { DismissalReason } from "../../types/detections";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";

const REASONS = Object.keys(DISMISSAL_LABELS) as DismissalReason[];

export function DismissDialog({
  open,
  busy,
  reason,
  note,
  onReason,
  onNote,
  onClose,
  onConfirm,
}: {
  open: boolean;
  busy: boolean;
  reason: DismissalReason | "";
  note: string;
  onReason: (value: DismissalReason) => void;
  onNote: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!open) {
    return null;
  }
  return (
    <Modal
      title="Dismiss detection"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} disabled={busy || !reason}>
            {busy ? "Dismissing…" : "Confirm dismiss"}
          </Button>
        </>
      }
    >
      <p className="text-sm text-ink-muted">
        Dismissing removes this row from the active investigation queue. It does not create or close an
        incident.
      </p>
      <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Reason
        <select
          value={reason}
          onChange={(event) => onReason(event.target.value as DismissalReason)}
          className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
        >
          <option value="">Select a reason</option>
          {REASONS.map((code) => (
            <option key={code} value={code}>
              {DISMISSAL_LABELS[code]}
            </option>
          ))}
        </select>
      </label>
      <label className="mt-3 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Note
        <textarea
          value={note}
          onChange={(event) => onNote(event.target.value)}
          rows={4}
          className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
        />
      </label>
    </Modal>
  );
}
