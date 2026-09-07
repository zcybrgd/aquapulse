import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { formatDateTime, formatNumber } from "../../lib/format";
import { EVIDENCE_TYPE_LABELS, RULE_LABELS, scorePercent } from "../../lib/detections";
import type { DetectionDetail, InvestigationAgentInputV1, InvestigationEventItem } from "../../types/detections";
import type { TelemetryHistoryResponse } from "../../types/telemetry";
import { DetectionEvidenceChart } from "./DetectionEvidenceChart";
import { InvestigationHistory } from "./InvestigationHistory";
import { InvestigationPanel, type InvestigationPanelProps } from "./InvestigationPanel";
import { DetectionPriorityBadge } from "./DetectionPriorityBadge";
import { DetectionStatusBadge } from "./DetectionStatusBadge";
import { SimulatedTelemetryBadge } from "../telemetry/TelemetryBadges";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { AssetStatusBadge } from "../assets/AssetStatusBadge";
import type { OperationalStatus } from "../../types/assets";

export function DetectionDetailView({
  detection,
  agentInput,
  history,
  events,
  busy,
  workflowError,
  workflowSuccess,
  onStartReview,
  onAddNote,
  onDismiss,
  onReopen,
  onMerge,
  onPromote,
}: {
  detection: DetectionDetail;
  agentInput: InvestigationAgentInputV1 | null;
  history: TelemetryHistoryResponse | null;
  events: InvestigationEventItem[];
  busy: boolean;
  workflowError: string | null;
  workflowSuccess: string | null;
  onStartReview: (note?: string) => Promise<unknown>;
  onAddNote: (note: string) => Promise<unknown>;
  onDismiss: InvestigationPanelProps["onDismiss"];
  onReopen: (note?: string) => Promise<unknown>;
  onMerge: InvestigationPanelProps["onMerge"];
  onPromote: InvestigationPanelProps["onPromote"];
}) {
  const location = useLocation();
  const [technicalOpen, setTechnicalOpen] = useState(false);
  const factors = detection.score_explanation.factors ?? {};
  const weighted = detection.score_explanation.weighted ?? {};
  const first = detection.evidence.find((item) => item.evidence_type === "first_value");
  const last = detection.evidence.find((item) => item.evidence_type === "last_value");

  return (
    <div className="flex flex-col gap-6">
      <div className="min-w-0">
        <Link
          to={`/detections${location.search}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-teal hover:underline"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          Back to Investigation Queue
        </Link>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-teal">{detection.detection_number}</p>
          <DetectionPriorityBadge priority={detection.priority} />
          {detection.awaiting_agent_investigation ? (
            <Badge className="bg-page text-ink-muted">Awaiting Investigation Agent result</Badge>
          ) : null}
          {detection.has_agent_finding ? <Badge className="bg-teal-light text-teal">Agent-assessed</Badge> : null}
          <DetectionStatusBadge status={detection.status} />
          <SimulatedTelemetryBadge />
        </div>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
          Score {scorePercent(detection.anomaly_score)}
        </h2>
        <p className="mt-1 text-sm text-ink-muted">Detected {formatDateTime(detection.detected_at)}</p>
        <p className="mt-2 text-sm text-ink-muted">
          Deterministic rule output is labelled Screening priority. Final classification, severity
          and confidence come from the Investigation Agent when a mapped finding exists.
        </p>
      </div>

      {!detection.agent_finding ? (
        <Card className="min-w-0 p-5">
          <h3 className="text-base font-semibold text-ink">Investigation Agent result</h3>
          <p className="mt-2 text-sm text-ink-muted">Awaiting Investigation Agent result</p>
        </Card>
      ) : null}

      {detection.agent_finding ? (
        <Card className="min-w-0 border-teal/30 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-ink">Investigation Agent result</h3>
            <Badge className="bg-teal-light text-teal">Agent-assessed</Badge>
          </div>
          <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-ink-muted">Agent classification</dt>
              <dd className="mt-0.5 font-medium text-ink">{detection.agent_finding.classification}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Agent severity tier</dt>
              <dd className="mt-0.5 font-medium text-ink">{detection.agent_finding.severity_tier}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Agent confidence</dt>
              <dd className="mt-0.5 font-medium text-ink">{detection.agent_finding.confidence_score}</dd>
            </div>
            {detection.agent_finding.anomaly_score != null ? (
              <div>
                <dt className="text-ink-muted">Agent anomaly score</dt>
                <dd className="mt-0.5 font-medium text-ink">{detection.agent_finding.anomaly_score}</dd>
              </div>
            ) : null}
            <div>
              <dt className="text-ink-muted">Mapping</dt>
              <dd className="mt-0.5 font-medium text-ink">{detection.agent_finding.mapping_status}</dd>
            </div>
          </dl>
          <p className="mt-3 text-sm text-ink">{detection.agent_finding.operator_justification ?? "No justification supplied."}</p>
          {detection.agent_finding.run_id ? (
            <Link
              to={`/agent-audit/runs/${encodeURIComponent(detection.agent_finding.run_id)}`}
              className="mt-3 inline-block text-sm font-medium text-teal hover:underline"
            >
              Open agent audit run {detection.agent_finding.run_id}
            </Link>
          ) : null}
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <Card className="min-w-0 p-5">
            <h3 className="text-base font-semibold text-ink">Why it triggered</h3>
            <p className="mt-2 text-sm text-ink">{detection.trigger_reason}</p>
            <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-ink-muted">Rule</dt>
                <dd className="mt-0.5 text-ink">
                  {RULE_LABELS[detection.rule_code] ?? detection.rule_name} · v{detection.rule_version}
                </dd>
              </div>
              <div>
                <dt className="text-ink-muted">Reason codes</dt>
                <dd className="mt-0.5 text-ink">{detection.reason_codes.join(", ") || "—"}</dd>
              </div>
              {first && last ? (
                <div className="sm:col-span-2">
                  <dt className="text-ink-muted">Before / after</dt>
                  <dd className="mt-0.5 text-ink">
                    {first.observed_value} {first.unit} → {last.observed_value} {last.unit}
                  </dd>
                </div>
              ) : null}
            </dl>
            <div className="mt-4">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Score components</p>
              <ul className="mt-2 space-y-1 text-sm">
                {Object.entries(weighted).map(([key, value]) => (
                  <li key={key} className="flex justify-between gap-3">
                    <span className="text-ink-muted">
                      {key.replaceAll("_", " ")}
                      {factors[key] != null ? ` (factor ${factors[key]})` : ""}
                    </span>
                    <span className="text-ink">{value.toFixed(3)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>

          <DetectionEvidenceChart detection={detection} history={history} />

          <Card className="min-w-0 p-5">
            <h3 className="text-base font-semibold text-ink">Evidence</h3>
            <ul className="mt-3 space-y-3">
              {detection.evidence.map((item, index) => (
                <li key={`${item.metric}-${item.evidence_type}-${index}`} className="rounded-2xl border border-line p-3">
                  <p className="text-sm font-medium text-ink">
                    {EVIDENCE_TYPE_LABELS[item.evidence_type] ?? item.evidence_type}
                  </p>
                  <p className="mt-1 text-sm text-ink-muted">
                    {item.metric}: {item.observed_value} {item.unit}
                    {item.threshold_value != null ? ` · threshold ${item.threshold_value}` : ""}
                    {item.baseline_value != null ? ` · baseline ${item.baseline_value}` : ""}
                  </p>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="mt-4 text-sm font-medium text-teal hover:underline"
              onClick={() => setTechnicalOpen((value) => !value)}
            >
              {technicalOpen ? "Hide technical evidence" : "Show technical evidence"}
            </button>
            {technicalOpen ? (
              <pre className="mt-3 overflow-x-auto rounded-2xl bg-page p-3 text-xs text-ink">
                {JSON.stringify(detection.evidence_summary, null, 2)}
              </pre>
            ) : null}
          </Card>
        </div>

        <div className="flex min-w-0 flex-col gap-4">
          <InvestigationPanel
            detection={detection}
            busy={busy}
            error={workflowError}
            success={workflowSuccess}
            onStartReview={onStartReview}
            onAddNote={onAddNote}
            onDismiss={onDismiss}
            onReopen={onReopen}
            onMerge={onMerge}
            onPromote={onPromote}
          />

          <Card className="min-w-0 p-5">
            <h3 className="text-base font-semibold text-ink">Context</h3>
            <div className="mt-2">
              <AssetStatusBadge status={detection.asset_status as OperationalStatus} />
            </div>
            <dl className="mt-3 space-y-2 text-sm">
              <Row label="Sensor" value={detection.sensor_id} />
              <Row label="Zone" value={detection.zone} />
              <Row label="Pipeline" value={detection.pipeline_segment ?? "—"} />
              <Row label="Criticality" value={detection.criticality != null ? `Tier ${detection.criticality}` : "—"} />
              <Row
                label="Population served"
                value={detection.population_served != null ? formatNumber(detection.population_served) : "—"}
              />
              <Row label="Freshness" value={detection.telemetry_freshness ?? "—"} />
              <Row
                label="Latest reading"
                value={detection.latest_reading_at ? formatDateTime(detection.latest_reading_at) : "—"}
              />
              <Row label="Linked incident" value={detection.incident_id ?? "None"} />
            </dl>
            {detection.incident_id ? (
              <Link
                to={`/incidents/${encodeURIComponent(detection.incident_id)}`}
                className="mt-3 inline-flex text-sm font-medium text-teal hover:underline"
              >
                View incident
              </Link>
            ) : null}
            <Link
              to={`/assets/${encodeURIComponent(detection.sensor_id)}`}
              className="mt-4 inline-flex text-sm font-medium text-teal hover:underline"
            >
              View asset details
            </Link>
          </Card>

          <Card className="min-w-0 p-5">
            <h3 className="text-base font-semibold text-ink">Related detections</h3>
            {detection.related_detections.length === 0 ? (
              <p className="mt-2 text-sm text-ink-muted">No overlapping detections for this sensor window.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {detection.related_detections.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={`/detections/${encodeURIComponent(item.id)}${location.search}`}
                      className="text-sm font-medium text-teal hover:underline"
                    >
                      {item.detection_number}
                    </Link>
                    <p className="text-xs text-ink-muted">{item.rule_code}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="min-w-0 p-5">
            <h3 className="text-base font-semibold text-ink">Future Investigation Agent input</h3>
            <p className="mt-1 text-sm text-ink-muted">
              No AI agent has run yet. This is a read-only contract preview for a future investigation step.
            </p>
            {agentInput ? (
              <dl className="mt-3 space-y-2 text-sm">
                <Row label="Schema" value={`v${agentInput.schema_version}`} />
                <Row label="Detection" value={agentInput.detection_id} />
                <Row label="Sensor" value={agentInput.sensor.id} />
                <Row
                  label="Window"
                  value={`${formatDateTime(agentInput.telemetry_window.start)} – ${formatDateTime(agentInput.telemetry_window.end)}`}
                />
                <Row label="Triggers" value={agentInput.rule_triggers.map((item) => item.rule_code).join(", ")} />
                <Row label="Criticality" value={agentInput.criticality != null ? String(agentInput.criticality) : "—"} />
                <Row label="Data mode" value={agentInput.data_mode} />
              </dl>
            ) : (
              <p className="mt-2 text-sm text-ink-muted">Agent input is unavailable.</p>
            )}
          </Card>

          <InvestigationHistory events={events} />
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted">{label}</dt>
      <dd className="text-right font-medium text-ink">{value}</dd>
    </div>
  );
}
