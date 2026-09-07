import { Link } from "react-router-dom";
import { RefreshCw, ShieldAlert } from "lucide-react";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { StatusDot } from "../components/ui/StatusDot";
import { useIntegrationReadiness } from "../hooks/useIntegrationReadiness";
import { formatDateTime } from "../lib/format";
import type { AgentSummary } from "../types/integrations";

function AgentCard({ agent }: { agent: AgentSummary }) {
  return (
    <Card className="min-w-0 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink">{agent.display_name}</h3>
          <p className="mt-1 text-sm text-ink-muted">{agent.agent_code}</p>
        </div>
        <StatusDot
          tone={agent.health_status === "healthy" ? "success" : "warning"}
          label={agent.health_status}
        />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-ink-muted">Mode</dt>
          <dd className="font-medium text-ink">{agent.mode}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Contract</dt>
          <dd className="font-medium text-ink">
            {agent.agent_code === "network_management_agent" ||
            agent.agent_code === "network_agent" ||
            agent.contract_version === "unconfirmed" ||
            agent.contract_version === "draft-unconfirmed"
              ? "Contract awaiting team confirmation"
              : agent.contract_version}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">URL configured</dt>
          <dd className="font-medium text-ink">{agent.url_configured ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Last health check</dt>
          <dd className="font-medium text-ink">
            {agent.last_health_check_at ? formatDateTime(agent.last_health_check_at) : "Never"}
          </dd>
        </div>
      </dl>
    </Card>
  );
}

export function IntegrationsPage() {
  const { data, loading, error, reload } = useIntegrationReadiness();
  const readiness = data?.readiness;

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Integration Readiness</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Contracts, mappings and safety gates for later agent connection. This page is read-only
            and cannot enable integrations.
          </p>
        </div>
        <Button variant="secondary" onClick={reload} disabled={loading}>
          <RefreshCw size={14} aria-hidden="true" />
          Refresh
        </Button>
      </div>

      {loading ? <Skeleton className="h-40 w-full" /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}

      {readiness ? (
        <>
          <Card className="border-teal/30 bg-teal-light p-5">
            <p className="text-sm font-semibold text-ink">{readiness.banner}</p>
            <p className="mt-2 text-sm text-ink-muted">{readiness.advisory_notice}</p>
            <p className="mt-1 text-sm text-ink-muted">{readiness.actuation_notice}</p>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">CAMARA</p>
              <p className="mt-2 font-semibold text-ink">
                {readiness.safety.camara_enabled ? "Enabled" : "Disabled"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Notifications</p>
              <p className="mt-2 font-semibold text-ink">
                {readiness.safety.notifications_enabled ? "Enabled" : "Disabled"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink-muted">
                <ShieldAlert size={14} aria-hidden="true" />
                Physical commands
              </p>
              <p className="mt-2 font-semibold text-ink">
                {readiness.safety.physical_commands_enabled ? "Enabled" : "Disabled"}
              </p>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {readiness.agents.map((agent) => (
              <AgentCard key={agent.agent_code} agent={agent} />
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="p-5">
              <h3 className="text-base font-semibold text-ink">Mapping coverage</h3>
              <p className="mt-3 text-sm text-ink-muted">
                Enabled mappings: {readiness.mapping_coverage.enabled_mappings}
              </p>
              <p className="mt-1 text-sm text-ink-muted">
                Unmapped findings: {readiness.mapping_coverage.unmapped_findings}
              </p>
              <p className="mt-3 text-sm text-ink-muted">
                Unknown external IDs stay unmapped. AquaPulse never guesses.
              </p>
            </Card>
            <Card className="p-5">
              <h3 className="text-base font-semibold text-ink">Contract documentation</h3>
              <p className="mt-3 text-sm text-ink-muted">
                Validation status: contracts are available and execution is disabled.
              </p>
              <a
                className="mt-3 inline-flex text-sm font-medium text-teal"
                href={`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/integrations/agents/contracts/investigation/v1`}
              >
                Investigation contract v1
              </a>
              <span className="mx-2 text-ink-muted">·</span>
              <a
                className="inline-flex text-sm font-medium text-teal"
                href={`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/integrations/agents/contracts/response/v1`}
              >
                Response contract v1
              </a>
            </Card>
          </div>

          <Card className="overflow-hidden p-0">
            <div className="border-b border-line px-5 py-4">
              <h3 className="text-base font-semibold text-ink">Last runs</h3>
            </div>
            {readiness.last_runs.length === 0 ? (
              <EmptyState title="No agent runs" description="Runs appear after a validated result is stored." />
            ) : (
              <ul className="divide-y divide-line">
                {readiness.last_runs.map((run) => (
                  <li key={run.run_id}>
                    <Link
                      to={`/integrations/runs/${run.run_id}`}
                      className="flex flex-col gap-1 px-5 py-3 text-sm hover:bg-page sm:flex-row sm:items-center sm:justify-between"
                    >
                      <span className="font-medium text-ink">{run.run_id}</span>
                      <span className="text-ink-muted">
                        {run.agent_type} · {run.status} · {run.mapping_warning_count} mapping warnings
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="overflow-hidden p-0">
              <div className="border-b border-line px-5 py-4">
                <h3 className="text-base font-semibold text-ink">Findings</h3>
                <p className="mt-1 text-sm text-ink-muted">Agent result is advisory</p>
              </div>
              {(data?.findings.length ?? 0) === 0 ? (
                <EmptyState title="No findings" description="Investigation results stay here as evidence only." />
              ) : (
                <ul className="divide-y divide-line">
                  {data?.findings.map((finding) => (
                    <li key={finding.id}>
                      <Link
                        to={`/integrations/findings/${finding.id}`}
                        className="block px-5 py-3 text-sm hover:bg-page"
                      >
                        <p className="font-medium text-ink">{finding.classification_label}</p>
                        <p className="text-ink-muted">
                          {finding.external_anomaly_id} · {finding.mapping_status}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card className="overflow-hidden p-0">
              <div className="border-b border-line px-5 py-4">
                <h3 className="text-base font-semibold text-ink">Recommendations</h3>
                <p className="mt-1 text-sm text-ink-muted">No physical command can be executed</p>
              </div>
              {(data?.recommendations.length ?? 0) === 0 ? (
                <EmptyState
                  title="No Response Agent recommendation available"
                  description="Waiting for integration. Recommendations appear after a validated Response Agent POST."
                />
              ) : (
                <ul className="divide-y divide-line">
                  {data?.recommendations.map((item) => (
                    <li key={item.id}>
                      <Link
                        to={`/integrations/recommendations/${item.id}`}
                        className="block px-5 py-3 text-sm hover:bg-page"
                      >
                        <p className="font-medium text-ink">{item.decision}</p>
                        <p className="text-ink-muted">
                          {item.external_result_id} · {item.safety_status}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
