import { Link, useParams } from "react-router-dom";

import { AuditRunHeader, AuditRunSummary } from "../components/agent-audit/AuditRunSummary";
import { AuditRunTimeline } from "../components/agent-audit/AuditRunTimeline";
import { IdentityMappingSection } from "../components/agent-audit/IdentityMappingSection";
import { InvestigationResultSection } from "../components/agent-audit/InvestigationFindingCard";
import { RawPayloadSection } from "../components/agent-audit/RawPayloadSection";
import { ResponseAgentResult } from "../components/agent-audit/ResponseAgentResult";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useAgentAuditRun } from "../hooks/useAgentAuditRun";
import { agentCodeLabel } from "../lib/agentAudit";
import {
  mappingRows,
  mappingWarningMessages,
  mergeInvestigationFindings,
  mergeResponseResult,
  rawPayload,
  readInvestigationBatch,
  validationLabel,
} from "../lib/agentAuditDisplay";

export function AgentAuditRunPage() {
  const { runId } = useParams();
  const { data, loading, error, notFound, reload } = useAgentAuditRun(runId);

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-[1400px] flex-col gap-6 overflow-x-hidden px-0">
      {!data ? (
        <Link to="/agent-audit" className="text-sm font-medium text-teal hover:underline">
          Back to Agent Audit Trail
        </Link>
      ) : null}
      {loading ? (
        <div className="flex flex-col gap-4" aria-busy="true" aria-label="Loading agent run">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-56 w-full" />
        </div>
      ) : null}

      {!loading && notFound ? (
        <EmptyState
          title="Agent run not found"
          description="This run does not exist. It may have been removed, or the URL is incorrect."
        />
      ) : null}
      {!loading && error && !notFound ? (
        <ErrorState title="Unable to load agent run" message={error} onRetry={reload} />
      ) : null}

      {!loading && data ? <AgentAuditRunDetails data={data} loading={loading} onRefresh={reload} /> : null}
    </div>
  );
}

function AgentAuditRunDetails({
  data,
  loading,
  onRefresh,
}: {
  data: NonNullable<ReturnType<typeof useAgentAuditRun>["data"]>;
  loading: boolean;
  onRefresh: () => void;
}) {
  const { run, integration, findings, recommendations } = data;
  const payload = integration?.response_payload ?? null;
  const batch = readInvestigationBatch(payload);
  const investigationFindings = mergeInvestigationFindings(run, findings, payload);
  const response =
    run.agent_type === "response_agent" ? mergeResponseResult(run, recommendations, payload) : null;
  const warnings = mappingWarningMessages(integration?.mapping_warnings ?? []);
  const identities = mappingRows(investigationFindings, response, integration?.mapping_warnings ?? []);
  const validation = validationLabel(run, integration);
  const supported = run.agent_type === "investigation_agent" || run.agent_type === "response_agent";
  const missingPayload = !payload;

  return (
    <>
      <AuditRunHeader run={run} loading={loading} onRefresh={onRefresh} />
      <AuditRunSummary
        run={run}
        integration={integration}
        validation={validation}
        warningCount={warnings.length || (integration?.mapping_warning_count ?? 0)}
      />

      {!supported ? (
        <EmptyState
          title="Unsupported agent type"
          description={`${agentCodeLabel(run.agent_code)} results are not rendered as an operator assessment.`}
        />
      ) : null}

      {supported && run.agent_type === "investigation_agent" && missingPayload && investigationFindings.length === 0 ? (
        <EmptyState title="Missing result payload" description="This run has no stored Investigation Agent result to display." />
      ) : null}

      {supported && run.agent_type === "investigation_agent" && (payload || investigationFindings.length > 0) ? (
        <InvestigationResultSection
          batchId={batch.batchId ?? run.source_public_id}
          analysisTimestamp={batch.analysisTimestamp}
          totalClustersAnalyzed={batch.totalClustersAnalyzed}
          anomaliesDetected={batch.anomaliesDetected}
          validation={validation}
          findings={investigationFindings}
        />
      ) : null}

      {supported && run.agent_type === "response_agent" && !response ? (
        <EmptyState title="Missing result payload" description="This run has no stored Response Agent recommendation to display." />
      ) : null}

      {supported && run.agent_type === "response_agent" && response ? <ResponseAgentResult result={response} /> : null}

      {integration && integration.validation_errors.length > 0 ? (
        <EmptyState
          title="Contract validation failure"
          description="This stored result contains validation errors. The raw sanitized payload is available below."
        />
      ) : null}

      <IdentityMappingSection rows={identities} warnings={warnings} />
      <AuditRunTimeline
        run={run}
        extras={{
          analysisTimestamp: batch.analysisTimestamp,
          completedAt: integration?.completed_at,
          findingCount: investigationFindings.length,
          recommendationCount: recommendations.length,
        }}
      />
      <RawPayloadSection payload={rawPayload(integration)} />
    </>
  );
}
