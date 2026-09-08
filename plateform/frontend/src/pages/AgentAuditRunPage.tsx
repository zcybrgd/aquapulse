import { Link, useParams } from "react-router-dom";

import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useAgentAuditRun } from "../hooks/useAgentAuditRun";
import { formatDateTime } from "../lib/format";
import type { AgentAuditEventDetail } from "../types/agentAudit";

const STAGE_LABELS: Record<string, string> = {
  lightweight_detection: "Screening result",
  anomaly_investigation: "Investigation Agent result",
  network_management: "Network Agent result",
  response: "Response Agent recommendation",
  platform_safety: "Platform safety decision",
  audit: "Audit",
};

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined || (typeof value === "object" && value !== null && Object.keys(value as object).length === 0)) {
    return <p className="text-sm text-ink-muted">Not supplied.</p>;
  }
  return (
    <pre className="max-h-64 overflow-auto rounded-xl bg-page p-3 text-xs text-ink">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function EventCard({ event }: { event: AgentAuditEventDetail }) {
  return (
    <Card className="min-w-0 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
        {STAGE_LABELS[event.pipeline_stage] ?? event.pipeline_stage}
      </p>
      <p className="mt-1 font-medium text-ink">{event.node_name ?? event.event_type}</p>
      <p className="text-sm text-ink-muted">
        {event.summary} · {event.status} · {formatDateTime(event.occurred_at)}
      </p>
      {event.error_message ? <p className="mt-2 text-sm text-critical">{event.error_message}</p> : null}
      {event.pipeline_stage === "platform_safety" ? (
        <p className="mt-2 text-sm font-medium text-critical">Blocked by AquaPulse safety policy</p>
      ) : null}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-medium text-ink">Sanitized input summary</summary>
        <div className="mt-2">
          <JsonBlock value={event.input_summary} />
        </div>
      </details>
      <details className="mt-2">
        <summary className="cursor-pointer text-sm font-medium text-ink">Sanitized output summary</summary>
        <div className="mt-2">
          <JsonBlock value={event.output_summary} />
        </div>
      </details>
      <div className="mt-3">
        <p className="text-sm font-medium text-ink">Agent-provided reasoning — not independently verified</p>
        <p className="mt-1 text-sm text-ink-muted">{event.reasoning_summary ?? "No reasoning was supplied."}</p>
        <details className="mt-2">
          <summary className="cursor-pointer text-sm text-ink-muted">Structured trace</summary>
          <div className="mt-2">
            <JsonBlock value={event.reasoning_trace} />
          </div>
        </details>
      </div>
    </Card>
  );
}

export function AgentAuditRunPage() {
  const { runId } = useParams();
  const { run, loading, error, notFound, reload } = useAgentAuditRun(runId);

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div>
        <Link to="/agent-audit" className="text-sm font-medium text-teal hover:underline">
          Back to Agent Audit Trail
        </Link>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink">{runId ?? "Agent run"}</h2>
      </div>

      {loading ? <Skeleton className="h-40 w-full" /> : null}
      {!loading && notFound ? <EmptyState title="Unknown run" description="That agent run was not found." /> : null}
      {!loading && error && !notFound ? <ErrorState message={error} onRetry={reload} /> : null}

      {run ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            {run.data_mode === "mock_agent_data" ? (
              <Badge className="bg-warning/15 text-ink">Mock agent data</Badge>
            ) : (
              <Badge className="bg-teal-light text-teal">Ingested result</Badge>
            )}
            {run.contract_unconfirmed ? (
              <Badge className="bg-page text-ink">Network Agent contract awaiting team confirmation</Badge>
            ) : null}
            {run.blocked ? <Badge className="bg-critical/10 text-critical">Platform safety: blocked</Badge> : null}
          </div>
          <Card className="p-5">
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <div>
                <dt className="text-ink-muted">Agent</dt>
                <dd className="font-medium text-ink">{run.agent_code}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Status</dt>
                <dd className="font-medium text-ink">{run.status}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Mapping</dt>
                <dd className="font-medium text-ink">{run.mapping_status ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Duration</dt>
                <dd className="font-medium text-ink">{run.duration_ms === null ? "—" : `${run.duration_ms} ms`}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Data mode</dt>
                <dd className="font-medium text-ink">{run.data_mode}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Notification</dt>
                <dd className="font-medium text-ink">{run.notification_sent ? "Reported sent" : "Not sent"}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Valve command</dt>
                <dd className="font-medium text-ink">
                  {run.valve_command_sent ? "Reported sent" : "Unchanged / not sent"}
                </dd>
              </div>
              <div>
                <dt className="text-ink-muted">Safety</dt>
                <dd className="font-medium text-ink">{run.safety_status ?? (run.blocked ? "blocked" : "—")}</dd>
              </div>
            </dl>
          </Card>

          {run.findings.length > 0 ? (
            <Card className="p-5">
              <h3 className="text-base font-semibold text-ink">Investigation Agent result</h3>
              <ul className="mt-3 space-y-3">
                {run.findings.map((finding) => (
                  <li key={`${finding.external_cluster_id}-${finding.classification}`} className="text-sm">
                    <p className="font-medium text-ink">
                      {finding.external_cluster_id ?? "Unmapped cluster"} · {finding.classification}
                    </p>
                    <p className="text-ink-muted">
                      Severity tier {finding.severity_tier} · Confidence {finding.confidence_score} · Mapping{" "}
                      {finding.mapping_status}
                    </p>
                    <p className="mt-1 text-ink-muted">{finding.operator_justification ?? "No justification supplied."}</p>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {run.recommendation_decisions.length > 0 ? (
            <Card className={run.decision === "AUTONOMOUS_ISOLATE" ? "border-critical/30 p-5" : "p-5"}>
              <h3 className="text-base font-semibold text-ink">Response Agent recommendation</h3>
              <ul className="mt-3 space-y-1 text-sm text-ink">
                <li>Decision: {run.recommendation_decisions.join(", ")}</li>
                <li>AquaPulse verification: unverified</li>
                <li>Real execution: disabled</li>
                <li>Valve command: {run.valve_command_sent ? "reported sent" : "not sent"}</li>
                <li>Notification: {run.notification_sent ? "reported sent" : "not sent"}</li>
                <li>Safety status: {run.safety_status ?? "—"}</li>
              </ul>
              <p className="mt-3 text-sm text-ink-muted">
                Stored as an advisory recommendation. AquaPulse does not execute a valve command.
              </p>
            </Card>
          ) : null}

          <section className="flex flex-col gap-3">
            <h3 className="text-base font-semibold text-ink">Chronological stage timeline</h3>
            {run.events.length === 0 ? (
              <EmptyState title="Partial audit timeline" description="This run has no stored audit events." />
            ) : (
              run.events.map((event) => <EventCard key={event.id} event={event} />)
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
