import { Link } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import { DISMISSAL_LABELS, EVENT_LABELS, STATUS_LABELS } from "../../lib/detections";
import type { DismissalReason, InvestigationEventItem } from "../../types/detections";
import { Card } from "../ui/Card";

export function InvestigationHistory({ events }: { events: InvestigationEventItem[] }) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Investigation history</h3>
      <p className="mt-1 text-sm text-ink-muted">Immutable operator actions. Events are append-only.</p>
      {events.length === 0 ? (
        <p className="mt-3 text-sm text-ink-muted">No investigation actions yet.</p>
      ) : (
        <ol className="mt-4 space-y-3">
          {events.map((event) => (
            <li key={event.id} className="rounded-2xl border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-ink">{EVENT_LABELS[event.event_type]}</p>
                <p className="text-xs text-ink-muted">{formatDateTime(event.created_at)}</p>
              </div>
              <p className="mt-1 text-xs text-ink-muted">{event.actor_name}</p>
              {event.from_status || event.to_status ? (
                <p className="mt-1 text-xs text-ink">
                  {event.from_status ? STATUS_LABELS[event.from_status] : "—"} →{" "}
                  {event.to_status ? STATUS_LABELS[event.to_status] : "—"}
                </p>
              ) : null}
              {event.reason_code ? (
                <p className="mt-1 text-xs text-ink">
                  Reason: {DISMISSAL_LABELS[event.reason_code as DismissalReason] ?? event.reason_code}
                </p>
              ) : null}
              {event.note ? <p className="mt-2 text-sm text-ink">{event.note}</p> : null}
              {event.target_detection_id ? (
                <Link
                  to={`/detections/${encodeURIComponent(event.target_detection_id)}`}
                  className="mt-2 inline-flex text-sm font-medium text-teal hover:underline"
                >
                  {event.target_detection_id}
                </Link>
              ) : null}
              {event.incident_id ? (
                <Link
                  to={`/incidents/${encodeURIComponent(event.incident_id)}`}
                  className="mt-2 inline-flex text-sm font-medium text-teal hover:underline"
                >
                  {event.incident_id}
                </Link>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
