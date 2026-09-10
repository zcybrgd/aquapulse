import { Link } from "react-router-dom";

import {
  classificationLabel,
  formatOptionalBoolean,
  formatOptionalInteger,
  formatOptionalNumber,
  formatOptionalPercent,
  formatOptionalText,
  formatOptionalTimestamp,
  networkField,
  formatEstimatedVolumeLoss,
  statusLabel,
  UNAVAILABLE,
  type InvestigationFindingView,
} from "../../lib/agentAuditDisplay";
import { SafeMarkdown } from "../../lib/safeMarkdown";
import { Card } from "../ui/Card";
import { AuditStatusBadge } from "./AuditStatusBadge";
import { MetricGrid, MetricItem } from "./MetricGrid";

const severityHint: Record<number, string> = {
  1: "Tier 1 / monitor",
  2: "Tier 2 / alert and human review",
  3: "Tier 3 / critical recommendation requiring platform safety policy",
};

export function FindingEvidenceSections({ finding }: { finding: InvestigationFindingView }) {
  const volumeLoss = formatEstimatedVolumeLoss(finding.physical);
  const reachable = networkField(finding.network, "device_reachable", "reachable");
  const camara = networkField(finding.network, "camara_reachability_status", "camara_reachability");
  const congestion = networkField(finding.network, "camara_congestion_level", "congestion_level");
  const apiUnavailable = networkField(finding.network, "api_unavailable");
  const degraded = networkField(finding.network, "network_degraded", "degraded");

  return (
    <div className="space-y-5">
        <section>
          <h4 className="text-sm font-semibold text-ink">Physical deviations</h4>
          <MetricGrid>
            <MetricItem label="Pressure drop" value={formatOptionalPercent(finding.physical.pressure_drop_pct)} hint="Percent pressure drop reported by the agent" />
            <MetricItem label="Flow surge" value={formatOptionalPercent(finding.physical.flow_surge_pct)} />
            <MetricItem label="Pressure slope" value={formatOptionalNumber(finding.physical.pressure_slope, 4, " psi/min")} />
            <MetricItem label="Flow slope" value={formatOptionalNumber(finding.physical.flow_slope, 4, " lps/min")} />
            <MetricItem label="Stale pre-outage data" value={formatOptionalBoolean(finding.physical.is_stale_pre_outage_data)} />
            {volumeLoss !== null ? <MetricItem label="Estimated volume loss" value={volumeLoss} /> : null}
          </MetricGrid>
        </section>

        <section>
          <h4 className="text-sm font-semibold text-ink">Criticality</h4>
          <MetricGrid>
            <MetricItem
              label="Criticality score"
              value={formatOptionalInteger(finding.criticality.criticality_score)}
              hint={severityHint[finding.severityTier]}
            />
            <MetricItem
              label="Proximity to reservoir"
              value={
                finding.criticality.proximity_to_reservoir_m == null
                  ? UNAVAILABLE
                  : `${formatOptionalNumber(finding.criticality.proximity_to_reservoir_m, 0)} m`
              }
            />
            <MetricItem label="Population served" value={formatOptionalInteger(finding.criticality.population_served)} />
            <MetricItem label="Associated valve ID" value={formatOptionalText(finding.valveId ?? finding.criticality.associated_valve_id)} />
            <MetricItem
              label="Pipe diameter"
              value={
                finding.criticality.pipe_diameter_mm == null
                  ? UNAVAILABLE
                  : `${formatOptionalNumber(finding.criticality.pipe_diameter_mm, 0)} mm`
              }
            />
          </MetricGrid>
        </section>

        <section>
          <h4 className="text-sm font-semibold text-ink">Network context</h4>
          <p className="mt-1 text-sm text-ink-muted">Network context reported by the Investigation Agent</p>
          <MetricGrid>
            {reachable !== undefined ? <MetricItem label="Device reachable" value={formatOptionalBoolean(reachable)} /> : null}
            {camara !== undefined ? <MetricItem label="CAMARA reachability" value={formatOptionalText(camara)} /> : null}
            {congestion !== undefined ? <MetricItem label="Congestion level" value={formatOptionalText(congestion)} /> : null}
            {apiUnavailable !== undefined ? <MetricItem label="API unavailable" value={formatOptionalBoolean(apiUnavailable)} /> : null}
            {degraded !== undefined ? <MetricItem label="Network degraded" value={formatOptionalBoolean(degraded)} /> : null}
            {reachable === undefined &&
            camara === undefined &&
            congestion === undefined &&
            apiUnavailable === undefined &&
            degraded === undefined ? (
              <MetricItem label="Network context" value={UNAVAILABLE} />
            ) : null}
          </MetricGrid>
        </section>
    </div>
  );
}

export function InvestigationFindingCard({ finding }: { finding: InvestigationFindingView }) {
  return (
    <details className="group min-w-0 rounded-2xl border border-line bg-white open:shadow-card">
      <summary className="cursor-pointer list-none px-4 py-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal [&::-webkit-details-marker]:hidden">
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <AuditStatusBadge value={finding.classification} label={classificationLabel(finding.classification)} />
            <AuditStatusBadge
              value={finding.severityTier === 3 ? "blocked" : finding.severityTier === 2 ? "validating" : "ready"}
              label={`Severity tier ${finding.severityTier}`}
            />
            <AuditStatusBadge value={finding.mappingStatus} label={statusLabel(finding.mappingStatus)} />
            <span className="text-xs text-ink-muted group-open:hidden">Show details</span>
            <span className="hidden text-xs text-ink-muted group-open:inline">Hide details</span>
          </div>
          <p className="text-sm font-medium text-critical">Agent assessment — not independently confirmed</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <p className="min-w-0 break-words text-sm text-ink">
              <span className="text-ink-muted">Sensor cluster </span>
              {finding.clusterId ?? UNAVAILABLE}
            </p>
            <p className="min-w-0 break-words text-sm text-ink">
              <span className="text-ink-muted">Segment </span>
              {finding.segmentId ?? UNAVAILABLE}
            </p>
          </div>
        </div>
      </summary>

      <div className="space-y-5 border-t border-line px-4 py-4">
        <FindingEvidenceSections finding={finding} />

        <section>
          <h4 className="text-sm font-semibold text-ink">Operator justification</h4>
          <p className="mt-1 text-sm text-ink-muted">Agent-provided justification — not independently verified</p>
          <div className="mt-2">
            {finding.justification ? (
              <SafeMarkdown text={finding.justification} />
            ) : (
              <p className="text-sm text-ink-muted">{UNAVAILABLE}</p>
            )}
          </div>
        </section>

        {finding.mappedDetectionId ? (
          <Link to={`/detections/${encodeURIComponent(finding.mappedDetectionId)}`} className="text-sm font-medium text-teal hover:underline">
            Open mapped detection {finding.mappedDetectionId}
          </Link>
        ) : null}
      </div>
    </details>
  );
}

export function InvestigationResultSection({
  batchId,
  analysisTimestamp,
  totalClustersAnalyzed,
  anomaliesDetected,
  validation,
  findings,
}: {
  batchId: string | null;
  analysisTimestamp: string | null;
  totalClustersAnalyzed: number | null;
  anomaliesDetected: number | null;
  validation: string;
  findings: InvestigationFindingView[];
}) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Investigation Agent result</h3>
      <MetricGrid>
        <MetricItem label="Batch ID" value={formatOptionalText(batchId)} />
        <MetricItem label="Analysis timestamp" value={formatOptionalTimestamp(analysisTimestamp)} />
        <MetricItem label="Total clusters analyzed" value={totalClustersAnalyzed === null ? UNAVAILABLE : formatOptionalInteger(totalClustersAnalyzed)} />
        <MetricItem label="Anomalies detected" value={anomaliesDetected === null ? UNAVAILABLE : formatOptionalInteger(anomaliesDetected)} />
        <MetricItem label="Stored findings" value={formatOptionalInteger(findings.length)} />
        <MetricItem label="Validation status" value={validation} />
      </MetricGrid>
      <div className="mt-5 space-y-3">
        {findings.length === 0 ? (
          <p className="text-sm text-ink-muted">No investigation findings were stored for this run.</p>
        ) : (
          findings.map((finding) => <InvestigationFindingCard key={finding.key} finding={finding} />)
        )}
      </div>
    </Card>
  );
}
