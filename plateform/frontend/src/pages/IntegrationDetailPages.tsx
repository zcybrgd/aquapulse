import { isAxiosError } from "axios";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchAgentFinding, fetchAgentRecommendation, fetchAgentRun } from "../api/integrations";
import { FindingEvidenceSections } from "../components/agent-audit/InvestigationFindingCard";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { investigationFindingView } from "../lib/agentAuditDisplay";
import { formatDateTime } from "../lib/format";
import type { AgentFindingRecord, AgentRecommendationRecord, AgentRunDetail } from "../types/integrations";

function isCanceled(caught: unknown): boolean {
  return isAxiosError(caught) && caught.code === "ERR_CANCELED";
}

function BackToQueue() {
  return (
    <Link to="/detections" className="text-sm font-medium text-teal">
      Back to Investigation Queue
    </Link>
  );
}

export function IntegrationRunPage() {
  const { runId = "" } = useParams();
  const [run, setRun] = useState<AgentRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!runId) {
      setError("This run could not be loaded.");
      return;
    }
    setError(null);
    try {
      setRun(await fetchAgentRun(runId, { signal }));
    } catch (caught: unknown) {
      if (isCanceled(caught)) return;
      setRun(null);
      setError("This run could not be loaded.");
    }
  }, [runId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!run) return <Skeleton className="h-48 w-full" />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <BackToQueue />
      <Card className="p-5">
        <h2 className="text-xl font-semibold text-ink">{run.run_id}</h2>
        <p className="mt-1 text-sm text-ink-muted">
          {run.agent_type} · {run.status} · {run.data_mode}
        </p>
        <p className="mt-3 text-sm text-ink-muted">Started {formatDateTime(run.started_at)}</p>
        <p className="mt-2 text-sm font-medium text-ink">Agent result is advisory</p>
        {run.mapping_warnings.length > 0 ? (
          <p className="mt-2 text-sm text-ink-muted">{run.mapping_warnings.length} mapping warning(s)</p>
        ) : null}
        <pre className="mt-4 overflow-x-auto rounded-xl bg-page p-3 text-xs text-ink">
          {JSON.stringify(run.response_payload, null, 2)}
        </pre>
      </Card>
    </div>
  );
}

export function IntegrationFindingPage() {
  const { findingId = "" } = useParams();
  const id = decodeURIComponent(findingId);
  const [finding, setFinding] = useState<AgentFindingRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!id) {
      setError("This finding could not be loaded.");
      return;
    }
    setError(null);
    try {
      setFinding(await fetchAgentFinding(id, { signal }));
    } catch (caught: unknown) {
      if (isCanceled(caught)) return;
      setFinding(null);
      setError("This finding could not be loaded.");
    }
  }, [id]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!finding) return <Skeleton className="h-48 w-full" />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <BackToQueue />
      <Card className="p-5">
        <h2 className="text-xl font-semibold text-ink">{finding.classification_label}</h2>
        <p className="mt-1 text-sm text-ink-muted">{finding.severity_label}</p>
        <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-ink-muted">Anomaly</dt>
            <dd className="mt-0.5 font-medium text-ink">{finding.external_anomaly_id}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Cluster</dt>
            <dd className="mt-0.5 font-medium text-ink">{finding.external_cluster_id ?? "Unmapped"}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Classification</dt>
            <dd className="mt-0.5 font-medium text-ink">{finding.classification}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Severity tier</dt>
            <dd className="mt-0.5 font-medium text-ink">{finding.severity_tier}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Mapping</dt>
            <dd className="mt-0.5 font-medium text-ink">
              {finding.mapping_status}
              {finding.mapped_detection_id ? ` · ${finding.mapped_detection_id}` : ""}
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-sm font-medium text-ink">Agent result is advisory</p>
        <p className="mt-2 text-sm text-ink-muted">{finding.operator_justification ?? "No justification supplied."}</p>
        <div className="mt-4">
          <FindingEvidenceSections finding={investigationFindingView(finding)} />
        </div>
        {finding.run_id ? (
          <Link
            to={`/agent-audit/runs/${encodeURIComponent(finding.run_id)}`}
            className="mt-4 inline-block text-sm font-medium text-teal hover:underline"
          >
            Open agent audit run {finding.run_id}
          </Link>
        ) : null}
      </Card>
    </div>
  );
}

export function IntegrationRecommendationPage() {
  const { recommendationId = "" } = useParams();
  const id = decodeURIComponent(recommendationId);
  const [item, setItem] = useState<AgentRecommendationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!id) {
      setError("This recommendation could not be loaded.");
      return;
    }
    setError(null);
    try {
      setItem(await fetchAgentRecommendation(id, { signal }));
    } catch (caught: unknown) {
      if (isCanceled(caught)) return;
      setItem(null);
      setError("This recommendation could not be loaded.");
    }
  }, [id]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!item) return <Skeleton className="h-48 w-full" />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <Link to="/integrations" className="text-sm font-medium text-teal">
        Back to Integrations
      </Link>
      <Card className="p-5">
        <h2 className="text-xl font-semibold text-ink">{item.decision}</h2>
        <p className="mt-1 text-sm text-ink-muted">
          {item.severity_label} · safety {item.safety_status}
        </p>
        <p className="mt-3 text-sm text-ink-muted">
          Valve reported sent={String(item.valve_command_sent)}, confirmed={String(item.valve_command_confirmed)},
          verified={String(item.valve_command_verified)}
        </p>
        <p className="mt-3 text-sm font-medium text-ink">No physical command can be executed</p>
      </Card>
    </div>
  );
}
