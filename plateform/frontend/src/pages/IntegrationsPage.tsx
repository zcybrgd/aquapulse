import { Link } from "react-router-dom";
import { RefreshCw, ShieldAlert } from "lucide-react";

import { AgentStatusCard } from "../components/integrations/AgentStatusCard";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useIntegrationReadiness } from "../hooks/useIntegrationReadiness";
import { useIntegrationStatus } from "../hooks/useIntegrationStatus";

export function IntegrationsPage() {
  const { data, loading, error, reload } = useIntegrationReadiness();
  const {
    data: status,
    loading: statusLoading,
    refreshing: statusRefreshing,
    error: statusError,
    reload: reloadStatus,
  } = useIntegrationStatus();
  const readiness = data?.readiness;
  const pageBusy = (loading && !data) || (statusLoading && !status);

  const refreshAll = () => {
    reload();
    reloadStatus();
  };

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Integration Readiness</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-muted">
            Live health and contract checks for connected agent services. This page is read-only
            and cannot enable integrations.
          </p>
        </div>
        <Button variant="secondary" onClick={refreshAll} disabled={pageBusy || statusRefreshing}>
          <RefreshCw size={14} aria-hidden="true" />
          Refresh
        </Button>
      </div>

      {pageBusy ? <Skeleton className="h-40 w-full" /> : null}
      {!pageBusy && statusError && !status ? <ErrorState message={statusError} onRetry={reloadStatus} /> : null}
      {!pageBusy && !statusError && error && !readiness ? <ErrorState message={error} onRetry={reload} /> : null}

      {status && !status.execution_globally_enabled ? (
        <Card className="border-warning/40 bg-warning/10 p-5">
          <p className="text-sm font-semibold text-ink">
            Agent services may be connected for readiness checks, but AquaPulse agent execution
            remains disabled.
          </p>
        </Card>
      ) : null}

      {status ? (
        <div className="grid gap-4 lg:grid-cols-3">
          {status.agents.map((agent) => (
            <AgentStatusCard
              key={agent.agent_type}
              agent={agent}
              checking={statusRefreshing}
              onCheckAgain={reloadStatus}
            />
          ))}
        </div>
      ) : null}

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
              <EmptyState
                title="No agent runs yet"
                description="Runs will appear after an external agent is connected and executed."
              />
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
                <EmptyState
                  title="No Investigation Agent findings available."
                  description="Findings appear after an external Investigation Agent posts a validated result."
                />
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
                  title="No Response Agent recommendations available."
                  description="Recommendations appear after an external Response Agent posts a validated result."
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
