import { Link } from "react-router-dom";

import {
  decisionLabel,
  formatOptionalBoolean,
  formatOptionalInteger,
  formatOptionalText,
  formatOptionalTimestamp,
  statusLabel,
  UNAVAILABLE,
  type ResponseResultView,
} from "../../lib/agentAuditDisplay";
import { Card } from "../ui/Card";
import { AuditStatusBadge } from "./AuditStatusBadge";
import { MetricGrid, MetricItem } from "./MetricGrid";

export function PlatformSafetyCard({ result }: { result: ResponseResultView }) {
  const isolationRequested = result.decision === "AUTONOMOUS_ISOLATE";
  const executed = result.valveCommandVerified;
  return (
    <Card className={`min-w-0 p-5 ${isolationRequested || result.safetyStatus === "blocked" ? "border-critical/30" : ""}`}>
      <h3 className="text-base font-semibold text-ink">Platform safety</h3>
      <p className="mt-1 text-sm text-ink-muted">
        AquaPulse owns authorization. Agent output is never treated as approval to actuate.
      </p>
      <MetricGrid>
        <MetricItem
          label="Recommendation status"
          value={result.decision ? decisionLabel(result.decision) : UNAVAILABLE}
        />
        <MetricItem
          label="Human approval status"
          value={
            result.humanOverrideRequested
              ? result.humanOverrideResponse
                ? `Requested — ${result.humanOverrideResponse}`
                : "Requested — no operator response recorded"
              : "Not requested"
          }
        />
        <MetricItem label="Execution status" value={executed ? "Independently verified" : "Not executed"} />
        <MetricItem label="Verification status" value="Unverified by AquaPulse" />
        {result.blockedReason ? <MetricItem label="Blocked reason" value={result.blockedReason} /> : null}
      </MetricGrid>
      {isolationRequested && !executed ? (
        <p className="mt-3 text-sm font-medium text-critical">
          Isolation was requested by the agent. AquaPulse has not independently verified or executed a valve command.
        </p>
      ) : null}
    </Card>
  );
}

export function ResponseAgentResult({ result }: { result: ResponseResultView }) {
  return (
    <div className="flex flex-col gap-4">
      <Card className="min-w-0 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold text-ink">Response Agent result</h3>
          {result.decision ? <AuditStatusBadge value={result.decision === "AUTONOMOUS_ISOLATE" ? "blocked" : "advisory"} label={decisionLabel(result.decision)} /> : null}
          {result.safetyStatus ? <AuditStatusBadge value={result.safetyStatus} label={statusLabel(result.safetyStatus)} /> : null}
        </div>
        <div className="mt-4">
          <MetricGrid>
            <MetricItem
              label="Incident ID"
              value={
                result.mappedIncident ? (
                  <Link to={`/incidents/${encodeURIComponent(result.mappedIncident)}`} className="text-teal hover:underline">
                    {result.mappedIncident}
                  </Link>
                ) : (
                  formatOptionalText(result.incidentId)
                )
              }
            />
            <MetricItem
              label="Device ID"
              value={
                result.mappedDevice ? (
                  <Link to={`/assets/${encodeURIComponent(result.mappedDevice)}`} className="text-teal hover:underline">
                    {result.mappedDevice}
                  </Link>
                ) : (
                  formatOptionalText(result.deviceId)
                )
              }
            />
            <MetricItem label="Cluster ID" value={formatOptionalText(result.clusterId)} />
            <MetricItem label="Severity tier" value={result.severityTier === null ? UNAVAILABLE : formatOptionalInteger(result.severityTier)} />
            <MetricItem label="Reachability" value={formatOptionalText(result.reachability)} />
            <MetricItem label="Decision" value={decisionLabel(result.decision)} />
            <MetricItem label="Operator message" value={formatOptionalText(result.operatorMessage)} />
            <MetricItem label="Human override requested" value={formatOptionalBoolean(result.humanOverrideRequested)} />
            <MetricItem label="Human override response" value={formatOptionalText(result.humanOverrideResponse)} />
            <MetricItem label="Notification sent" value={result.notificationSent ? "Reported sent" : "Not sent"} />
            <MetricItem label="Valve command sent" value={result.valveCommandSent ? "Reported sent" : "Not sent"} />
            <MetricItem label="Valve command confirmed" value={result.valveCommandConfirmed ? "Reported confirmed" : "Not confirmed"} />
            <MetricItem label="Created" value={formatOptionalTimestamp(result.createdAt)} />
          </MetricGrid>
        </div>
        <div className="mt-5">
          <h4 className="text-sm font-semibold text-ink">Reasoning</h4>
          <p className="mt-1 text-sm text-ink-muted">Agent-provided reasoning — not independently verified</p>
          {result.reasoningSteps.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">{UNAVAILABLE}</p>
          ) : (
            <ol className="mt-3 space-y-2">
              {result.reasoningSteps.map((step, index) => (
                <li key={`${step}-${index}`} className="rounded-xl bg-page px-3 py-2 text-sm text-ink">
                  <span className="mr-2 text-ink-muted">{index + 1}.</span>
                  {step}
                </li>
              ))}
            </ol>
          )}
        </div>
      </Card>
      <PlatformSafetyCard result={result} />
    </div>
  );
}
