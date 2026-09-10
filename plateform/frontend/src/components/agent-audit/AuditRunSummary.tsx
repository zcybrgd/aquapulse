import { RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import {
  agentCodeLabel,
  dataModeLabel,
  formatOptionalInteger,
  formatOptionalTimestamp,
  statusLabel,
  UNAVAILABLE,
} from "../../lib/agentAuditDisplay";
import type { AgentAuditRunDetail } from "../../types/agentAudit";
import type { AgentRunDetail } from "../../types/integrations";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { AuditStatusBadge } from "./AuditStatusBadge";
import { MetricGrid, MetricItem } from "./MetricGrid";

export function AuditRunHeader({
  run,
  loading,
  onRefresh,
}: {
  run: AgentAuditRunDetail;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <Link to="/agent-audit" className="text-sm font-medium text-teal hover:underline">
          Back to Agent Audit Trail
        </Link>
        <h2 className="mt-3 break-words text-2xl font-semibold tracking-tight text-ink">{run.public_id}</h2>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <p className="font-medium text-ink">{agentCodeLabel(run.agent_code)}</p>
          <AuditStatusBadge value={run.status} label={statusLabel(run.status)} />
          <AuditStatusBadge value={run.data_mode} label={dataModeLabel(run.data_mode)} />
        </div>
      </div>
      <Button variant="secondary" onClick={onRefresh} disabled={loading}>
        <RefreshCw size={14} aria-hidden="true" />
        Refresh
      </Button>
    </div>
  );
}

export function AuditRunSummary({
  run,
  integration,
  validation,
  warningCount,
}: {
  run: AgentAuditRunDetail;
  integration: AgentRunDetail | null;
  validation: string;
  warningCount: number;
}) {
  const startedAt = integration?.started_at ?? run.started_at;
  const completedAt = integration?.completed_at ?? null;
  const durationMs = run.duration_ms ?? integration?.duration_ms ?? null;
  const duration = startedAt && completedAt && durationMs !== null ? `${durationMs} ms` : UNAVAILABLE;

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Run summary</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Lifecycle timestamps describe the stored run. They are not agent audit events.
      </p>
      <div className="mt-4">
        <MetricGrid>
          <MetricItem label="Agent" value={agentCodeLabel(run.agent_code)} />
          <MetricItem label="Status" value={statusLabel(run.status)} />
          <MetricItem label="Data mode" value={dataModeLabel(run.data_mode)} />
          <MetricItem label="Contract version" value={run.contract_version} />
          <MetricItem label="Started" value={formatOptionalTimestamp(startedAt)} />
          {completedAt ? <MetricItem label="Completed" value={formatOptionalTimestamp(completedAt)} /> : null}
          {startedAt && completedAt ? <MetricItem label="Duration" value={duration} /> : null}
          <MetricItem label="Validation status" value={validation} />
          <MetricItem label="Mapping warnings" value={formatOptionalInteger(warningCount)} />
        </MetricGrid>
      </div>
    </Card>
  );
}
