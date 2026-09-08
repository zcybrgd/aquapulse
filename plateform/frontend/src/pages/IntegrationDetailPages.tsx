import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchAgentFinding, fetchAgentRecommendation, fetchAgentRun } from "../api/integrations";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { formatDateTime } from "../lib/format";
import type { AgentFindingRecord, AgentRecommendationRecord, AgentRunDetail } from "../types/integrations";

function BackLink() {
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

  useEffect(() => {
    const controller = new AbortController();
    void fetchAgentRun(runId, { signal: controller.signal })
      .then(setRun)
      .catch(() => setError("This run could not be loaded."));
    return () => controller.abort();
  }, [runId]);

  if (error) return <ErrorState message={error} />;
  if (!run) return <Skeleton className="h-48 w-full" />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <BackLink />
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
  const [finding, setFinding] = useState<AgentFindingRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchAgentFinding(findingId, { signal: controller.signal })
      .then(setFinding)
      .catch(() => setError("This finding could not be loaded."));
    return () => controller.abort();
  }, [findingId]);

  if (error) return <ErrorState message={error} />;
  if (!finding) return <Skeleton className="h-48 w-full" />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <BackLink />
      <Card className="p-5">
        <h2 className="text-xl font-semibold text-ink">{finding.classification_label}</h2>
        <p className="mt-1 text-sm text-ink-muted">{finding.severity_label}</p>
        <p className="mt-3 text-sm text-ink">Anomaly {finding.external_anomaly_id}</p>
        <p className="mt-1 text-sm text-ink-muted">
          Mapping {finding.mapping_status}
          {finding.mapped_detection_id ? ` · ${finding.mapped_detection_id}` : ""}
        </p>
        <p className="mt-3 text-sm font-medium text-ink">Agent result is advisory</p>
        <p className="mt-2 text-sm text-ink-muted">{finding.operator_justification}</p>
      </Card>
    </div>
  );
}

export function IntegrationRecommendationPage() {
  const { recommendationId = "" } = useParams();
  const [item, setItem] = useState<AgentRecommendationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchAgentRecommendation(recommendationId, { signal: controller.signal })
      .then(setItem)
      .catch(() => setError("This recommendation could not be loaded."));
    return () => controller.abort();
  }, [recommendationId]);

  if (error) return <ErrorState message={error} />;
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
