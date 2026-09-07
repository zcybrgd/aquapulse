import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusDot } from "../components/ui/StatusDot";
import { useAgentAuditData } from "../hooks/useAgentAuditData";
import { useAgentAuditFilters } from "../hooks/useAgentAuditFilters";
import { formatDateTime, formatNumber } from "../lib/format";

function displayCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return formatNumber(value, value % 1 === 0 ? 0 : 1);
}

export function AgentAuditPage() {
  const { filters, setFilters, clearFilters, hasActiveFilters } = useAgentAuditFilters();
  const { summary, runs, loading, refreshing, error, updatedAt, reload } = useAgentAuditData(filters);
  const items = runs?.items ?? [];

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Agent Audit Trail</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Ingested Investigation and Response agent runs. Seeded mock findings are hidden. This
            log does not replace operator history.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Badge className="bg-teal-light text-teal">Ingested results</Badge>
          <StatusDot label="Advisory only" />
          <p className="text-ink-muted">Updated {updatedAt ? formatDateTime(updatedAt.toISOString()) : "—"}</p>
          <Button variant="secondary" onClick={reload} disabled={loading || refreshing}>
            <RefreshCw size={14} aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Agent
          <select
            value={filters.agent_code}
            onChange={(event) => setFilters({ agent_code: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All agents</option>
            <option value="investigation_agent">Investigation Agent</option>
            <option value="response_agent">Response Agent</option>
            <option value="network_management_agent">Network Management Agent (unconfirmed)</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Status
          <select
            value={filters.status}
            onChange={(event) => setFilters({ status: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All statuses</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
            <option value="rejected">Rejected</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Decision
          <select
            value={filters.decision}
            onChange={(event) => setFilters({ decision: event.target.value })}
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          >
            <option value="">All decisions</option>
            <option value="LOG_ONLY">LOG_ONLY</option>
            <option value="ALERT_AND_AWAIT">ALERT_AND_AWAIT</option>
            <option value="AUTONOMOUS_ISOLATE">AUTONOMOUS_ISOLATE</option>
            <option value="ESCALATE_UNREACHABLE">ESCALATE_UNREACHABLE</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Incident
          <input
            value={filters.incident}
            onChange={(event) => setFilters({ incident: event.target.value })}
            placeholder="INC-1835"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Detection
          <input
            value={filters.detection}
            onChange={(event) => setFilters({ detection: event.target.value })}
            placeholder="DET-000001"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted">
          Device
          <input
            value={filters.device}
            onChange={(event) => setFilters({ device: event.target.value })}
            placeholder="VLV-CRN-014"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-ink-muted md:col-span-2">
          Search
          <input
            value={filters.search}
            onChange={(event) => setFilters({ search: event.target.value })}
            placeholder="Run ID, node, or error"
            className="h-10 rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink"
          />
        </label>
        {hasActiveFilters ? (
          <div className="flex items-end">
            <Button variant="ghost" onClick={clearFilters}>
              Clear filters
            </Button>
          </div>
        ) : null}
      </div>

      {loading ? <Skeleton className="h-40 w-full" /> : null}
      {!loading && error ? <ErrorState title="Unable to load agent audit" message={error} onRetry={reload} /> : null}

      {summary ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Total runs</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{displayCount(summary.total_runs)}</p>
          </Card>
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Successful</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{displayCount(summary.successful_runs)}</p>
          </Card>
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Failed</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{displayCount(summary.failed_runs)}</p>
          </Card>
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Blocked actions</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{displayCount(summary.blocked_actions)}</p>
          </Card>
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Average duration</p>
            <p className="mt-2 text-2xl font-semibold text-ink">
              {summary.average_duration_ms === null ? "—" : `${formatNumber(summary.average_duration_ms, 0)} ms`}
            </p>
          </Card>
          <Card className="min-w-0 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Last activity</p>
            <p className="mt-2 text-lg font-semibold text-ink">
              {summary.last_run_at ? formatDateTime(summary.last_run_at) : "—"}
            </p>
          </Card>
        </div>
      ) : null}

      {!loading && items.length === 0 ? (
        <EmptyState
          title="No ingested agent runs"
          description="Runs appear here after the Investigation or Response agent posts results."
        />
      ) : null}

      {items.length > 0 ? (
        <>
          <Card className="hidden min-w-0 overflow-x-auto p-0 md:block">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-page text-ink-muted">
                <tr>
                  {["Run", "Stages", "Agent", "Contract", "Status", "Classification", "Severity", "Decision", "Related", "Duration", "Started", "Data mode", ""].map((head) => (
                    <th key={head || "action"} className="px-4 py-3 font-medium">
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((run) => (
                  <tr key={run.id} className="border-t border-line">
                    <td className="px-4 py-3 font-medium text-ink">{run.public_id}</td>
                    <td className="px-4 py-3 text-ink-muted">{run.pipeline_stages.join(" → ") || "—"}</td>
                    <td className="px-4 py-3">{run.agent_code}</td>
                    <td className="px-4 py-3">{run.contract_unconfirmed ? "unconfirmed" : run.contract_version}</td>
                    <td className="px-4 py-3">{run.status}</td>
                    <td className="px-4 py-3">{run.classification ?? "—"}</td>
                    <td className="px-4 py-3">{run.investigation_severity ?? "—"}</td>
                    <td className="px-4 py-3">{run.decision ?? "—"}</td>
                    <td className="px-4 py-3">
                      {run.external_cluster_id ?? run.related_device ?? run.related_detection ?? "—"}
                    </td>
                    <td className="px-4 py-3">{run.duration_ms === null ? "—" : `${run.duration_ms} ms`}</td>
                    <td className="px-4 py-3">{formatDateTime(run.started_at)}</td>
                    <td className="px-4 py-3">{run.data_mode}</td>
                    <td className="px-4 py-3">
                      <Link to={`/agent-audit/runs/${run.public_id}`} className="font-medium text-teal hover:underline">
                        View audit
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((run) => (
              <Card key={run.id} className="p-4">
                <p className="font-medium text-ink">{run.public_id}</p>
                <p className="mt-1 text-sm text-ink-muted">
                  {run.agent_code} · {run.status} · {run.decision ?? "No decision"} · {run.data_mode}
                </p>
                {run.blocked ? <p className="mt-1 text-sm text-critical">Blocked by AquaPulse safety policy</p> : null}
                {run.contract_unconfirmed ? (
                  <p className="mt-1 text-sm text-ink-muted">Contract awaiting team confirmation</p>
                ) : null}
                <Link to={`/agent-audit/runs/${run.public_id}`} className="mt-3 inline-block text-sm font-medium text-teal">
                  View audit
                </Link>
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
