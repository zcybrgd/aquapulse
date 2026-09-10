import type { AgentAuditRunDetail } from "../../types/agentAudit";
import {
  auditTimelineHeading,
  runTimelineItems,
  statusLabel,
  type RunTimelineExtras,
  type RunTimelineItem,
} from "../../lib/agentAuditDisplay";
import { formatDateTime } from "../../lib/format";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { AuditStatusBadge } from "./AuditStatusBadge";

function TimelineCard({ item }: { item: RunTimelineItem }) {
  return (
    <Card className="min-w-0 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          {item.stage} · {item.eventType.replaceAll("_", " ")}
        </p>
        <AuditStatusBadge value={item.status} label={statusLabel(item.status)} />
      </div>
      <p className="mt-1 font-medium text-ink">{item.title}</p>
      <p className="text-sm text-ink-muted">
        {item.agentLabel} · {formatDateTime(item.occurredAt)}
      </p>
      <p className="mt-2 text-sm text-ink">{item.summary}</p>
      {item.warning ? <p className="mt-2 text-sm text-warning">{item.warning}</p> : null}
      {item.errorCode ? <p className="mt-2 text-sm text-warning">Validation / mapping: {item.errorCode}</p> : null}
    </Card>
  );
}

export function AuditRunTimeline({
  run,
  extras = {},
}: {
  run: AgentAuditRunDetail;
  extras?: RunTimelineExtras;
}) {
  const items = runTimelineItems(run, extras);
  const heading = auditTimelineHeading(run);
  const derived = items.length > 0 && items.every((item) => item.derived);

  if (items.length === 0) {
    return (
      <section>
        <h3 className="text-base font-semibold text-ink">Audit timeline</h3>
        <EmptyState
          title="No audit events recorded"
          description="No start time or audit events are stored for this run."
        />
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h3 className="text-base font-semibold text-ink">{heading}</h3>
        {derived ? (
          <p className="mt-1 text-sm text-ink-muted">
            Derived from the stored run. The agent did not emit per-stage audit events.
          </p>
        ) : null}
      </div>
      {items.map((item) => (
        <TimelineCard key={item.key} item={item} />
      ))}
    </section>
  );
}
