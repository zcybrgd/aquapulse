import { useState } from "react";
import { Link } from "react-router-dom";

import { useActorName } from "../../hooks/useActorName";
import { formatDateTime } from "../../lib/format";
import { DISMISSAL_LABELS } from "../../lib/detections";
import type { DetectionDetail, DismissalReason } from "../../types/detections";
import type { IncidentClassification, SeverityTier } from "../../types/incidents";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { DetectionStatusBadge } from "./DetectionStatusBadge";
import { DismissDialog } from "./DismissDialog";
import { MergeDialog } from "./MergeDialog";
import { defaultPromotePayload, PromoteDialog } from "./PromoteDialog";

export interface InvestigationPanelProps {
  detection: DetectionDetail;
  busy: boolean;
  error: string | null;
  success: string | null;
  onStartReview: (note?: string) => Promise<unknown>;
  onAddNote: (note: string) => Promise<unknown>;
  onDismiss: (reason: DismissalReason, note?: string) => Promise<unknown>;
  onReopen: (note?: string) => Promise<unknown>;
  onMerge: (targetId: string, note?: string) => Promise<unknown>;
  onPromote: (payload: {
    title: string;
    severity: SeverityTier;
    classification: IncidentClassification;
    summary: string;
    note?: string;
  }) => Promise<unknown>;
}

export function InvestigationPanel({
  detection,
  busy,
  error,
  success,
  onStartReview,
  onAddNote,
  onDismiss,
  onReopen,
  onMerge,
  onPromote,
}: InvestigationPanelProps) {
  const { actorName, setActorName, raw } = useActorName();
  const [note, setNote] = useState("");
  const [dismissOpen, setDismissOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [promoteOpen, setPromoteOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState<DismissalReason | "">("");
  const [dismissNote, setDismissNote] = useState("");
  const [mergeTarget, setMergeTarget] = useState("");
  const [mergeNote, setMergeNote] = useState("");
  const defaults = defaultPromotePayload(detection);
  const [promoteTitle, setPromoteTitle] = useState(defaults.title);
  const [promoteSeverity, setPromoteSeverity] = useState<SeverityTier>(defaults.severity);
  const [promoteClassification, setPromoteClassification] = useState<IncidentClassification>(
    defaults.classification,
  );
  const [promoteSummary, setPromoteSummary] = useState(defaults.summary);
  const [promoteNote, setPromoteNote] = useState("");
  const [promoteConfirmed, setPromoteConfirmed] = useState(false);
  const actions = new Set(detection.allowed_actions);
  const terminal = detection.status === "promoted" || detection.status === "merged";

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Investigation</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Human workflow only. A detection is not a confirmed incident. Actor name is a temporary
        development identity, not authentication.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <DetectionStatusBadge status={detection.status} />
        {detection.incident_id ? (
          <Link
            to={`/incidents/${encodeURIComponent(detection.incident_id)}`}
            className="text-sm font-medium text-teal hover:underline"
          >
            View incident {detection.incident_id}
          </Link>
        ) : null}
        {detection.merged_into_detection_id ? (
          <Link
            to={`/detections/${encodeURIComponent(detection.merged_into_detection_id)}`}
            className="text-sm font-medium text-teal hover:underline"
          >
            View merged detection {detection.merged_into_detection_id}
          </Link>
        ) : null}
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Reviewed by</dt>
          <dd className="text-right text-ink">{detection.reviewed_by ?? "—"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Review started</dt>
          <dd className="text-right text-ink">
            {detection.review_started_at ? formatDateTime(detection.review_started_at) : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Last update</dt>
          <dd className="text-right text-ink">
            {detection.updated_at ? formatDateTime(detection.updated_at) : "—"}
          </dd>
        </div>
        {detection.dismissal_reason ? (
          <div className="flex justify-between gap-3">
            <dt className="text-ink-muted">Dismissal</dt>
            <dd className="text-right text-ink">{DISMISSAL_LABELS[detection.dismissal_reason as DismissalReason]}</dd>
          </div>
        ) : null}
      </dl>

      <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
        Actor name (temporary)
        <input
          value={raw}
          onChange={(event) => setActorName(event.target.value)}
          maxLength={120}
          disabled={terminal}
          className="h-10 rounded-xl border border-line px-3 text-sm font-normal text-ink disabled:bg-page"
        />
      </label>

      {error ? (
        <p className="mt-3 rounded-2xl bg-critical/10 px-3 py-2 text-sm text-critical" role="alert">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="mt-3 rounded-2xl bg-success/10 px-3 py-2 text-sm text-success" role="status">
          {success}
        </p>
      ) : null}

      {!terminal ? (
        <>
          <label className="mt-4 flex flex-col gap-1 text-xs font-medium text-ink-muted">
            Investigation note
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={4}
              className="rounded-xl border border-line px-3 py-2 text-sm font-normal text-ink"
              placeholder="Add an operator note. Notes do not change status."
            />
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            {actions.has("add_note") ? (
              <Button
                disabled={busy || !note.trim()}
                onClick={async () => {
                  const result = await onAddNote(note.trim());
                  if (result) {
                    setNote("");
                  }
                }}
              >
                Add note
              </Button>
            ) : null}
            {actions.has("start_review") ? (
              <Button variant="secondary" disabled={busy} onClick={() => void onStartReview(note.trim() || undefined)}>
                Start review
              </Button>
            ) : null}
            {actions.has("reopen") ? (
              <Button variant="secondary" disabled={busy} onClick={() => void onReopen(note.trim() || undefined)}>
                Reopen
              </Button>
            ) : null}
            {actions.has("dismiss") ? (
              <Button variant="danger" disabled={busy} onClick={() => setDismissOpen(true)}>
                Dismiss
              </Button>
            ) : null}
            {actions.has("merge") ? (
              <Button variant="secondary" disabled={busy} onClick={() => setMergeOpen(true)}>
                Merge
              </Button>
            ) : null}
            {actions.has("promote") ? (
              <Button disabled={busy} onClick={() => setPromoteOpen(true)}>
                Promote to incident
              </Button>
            ) : null}
          </div>
        </>
      ) : (
        <p className="mt-4 text-sm text-ink-muted">This detection is closed. History and evidence stay readable.</p>
      )}

      <DismissDialog
        open={dismissOpen}
        busy={busy}
        reason={dismissReason}
        note={dismissNote}
        onReason={setDismissReason}
        onNote={setDismissNote}
        onClose={() => setDismissOpen(false)}
        onConfirm={async () => {
          if (!dismissReason) {
            return;
          }
          const result = await onDismiss(dismissReason, dismissNote.trim() || undefined);
          if (result) {
            setDismissOpen(false);
          }
        }}
      />
      <MergeDialog
        open={mergeOpen}
        busy={busy}
        currentId={detection.id}
        selectedId={mergeTarget}
        note={mergeNote}
        onSelect={setMergeTarget}
        onNote={setMergeNote}
        onClose={() => setMergeOpen(false)}
        onConfirm={async () => {
          if (!mergeTarget) {
            return;
          }
          const result = await onMerge(mergeTarget, mergeNote.trim() || undefined);
          if (result) {
            setMergeOpen(false);
          }
        }}
      />
      <PromoteDialog
        open={promoteOpen}
        busy={busy}
        detection={detection}
        title={promoteTitle}
        severity={promoteSeverity}
        classification={promoteClassification}
        summary={promoteSummary}
        note={promoteNote}
        confirmed={promoteConfirmed}
        onTitle={setPromoteTitle}
        onSeverity={setPromoteSeverity}
        onClassification={setPromoteClassification}
        onSummary={setPromoteSummary}
        onNote={setPromoteNote}
        onConfirmed={setPromoteConfirmed}
        onClose={() => setPromoteOpen(false)}
        onConfirm={async () => {
          const result = await onPromote({
            title: promoteTitle.trim(),
            severity: promoteSeverity,
            classification: promoteClassification,
            summary: promoteSummary.trim(),
            note: promoteNote.trim() || undefined,
          });
          if (result) {
            setPromoteOpen(false);
          }
        }}
      />
      <p className="mt-3 hidden text-[11px] text-ink-muted">{actorName}</p>
    </Card>
  );
}
