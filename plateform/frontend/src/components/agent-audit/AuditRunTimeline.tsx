import type { AgentAuditEventDetail, AgentAuditRunDetail } from "../../types/agentAudit";
import { agentCodeLabel, eventTypeLabel, stageLabel } from "../../lib/agentAudit";
import { auditTimelineHeading, eventWarning, statusLabel } from "../../lib/agentAuditDisplay";
import { formatDateTime } from "../../lib/format";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { AuditStatusBadge } from "./AuditStatusBadge";

function EventCard({ event }: { event: AgentAuditEventDetail }) {
  const warning = eventWarning(event);
  return (
    <Card className="min-w-0 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          {stageLabel(event.pipeline_stage)} · {event.event_type.replaceAll("_", " ")}
        </p>
        <AuditStatusBadge value={event.status} label={statusLabel(event.status)} />
      </div>
      <p className="mt-1 font-medium text-ink">{eventTypeLabel(event)}</p>
      <p className="text-sm text-ink-muted">
        {agentCodeLabel(event.agent_code)} · {formatDateTime(event.occurred_at)}
      </p>
      <p className="mt-2 text-sm text-ink">{event.summary}</p>
      {warning ? <p className="mt-2 text-sm text-warning">{warning}</p> : null}
      {event.error_code ? <p className="mt-2 text-sm text-warning">Validation / mapping: {event.error_code}</p> : null}
    </Card>
  );
}

export function AuditRunTimeline({ run }: { run: AgentAuditRunDetail }) {
  const heading = auditTimelineHeading(run);
  if (run.events.length === 0) {
    return (
      <section>
        <h3 className="text-base font-semibold text-ink">Audit timeline</h3>
        <EmptyState title="No audit events recorded" description="Events will appear here after a real agent run." />
      </section>
    );
  }
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-base font-semibold text-ink">{heading}</h3>
      {run.events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </section>
  );
}
