import { ClipboardList, Hourglass, Search, TriangleAlert, Waves } from "lucide-react";

import { formatDateTime, formatNumber } from "../../lib/format";
import type { DetectionQueueStats } from "../../types/detections";
import { KpiCard } from "../dashboard/KpiCard";
import { SimulatedTelemetryBadge } from "../telemetry/TelemetryBadges";
import { StatusDot } from "../ui/StatusDot";

interface DetectionQueueHeaderProps {
  stats: DetectionQueueStats | null;
  ready?: boolean;
  findingCount?: number;
  ingestReady?: boolean;
}

export function DetectionQueueHeader({
  stats,
  ready = true,
  findingCount = 0,
  ingestReady: _ingestReady = false,
}: DetectionQueueHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">Investigation Queue</h2>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Live Investigation Agent results land here after ingest. Screening rules stay on a
          separate tab and are not agent verdicts. A finding is advisory, not a confirmed incident.
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <SimulatedTelemetryBadge />
          <p className="text-xs text-ink-muted">
            Last detection run{" "}
            {ready && stats?.last_run_at ? formatDateTime(stats.last_run_at) : "not yet run"}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p className="text-ink-muted">
          <span className="font-semibold text-ink">{findingCount}</span> agent results
        </p>
        <StatusDot label={findingCount > 0 ? "Investigation Agent results" : "Waiting for integration"} />
      </div>
    </div>
  );
}

export function DetectionSummaryCards({ stats }: { stats: DetectionQueueStats }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      <KpiCard label="New" value={formatNumber(stats.new)} context="Awaiting review" icon={ClipboardList} delay={0.02} />
      <KpiCard
        label="Queued"
        value={formatNumber(stats.queued)}
        context="Reopened or waiting"
        icon={Hourglass}
        delay={0.04}
      />
      <KpiCard
        label="Under review"
        value={formatNumber(stats.under_review)}
        context="Opened by operators"
        icon={Search}
        delay={0.06}
      />
      <KpiCard
        label="High priority"
        value={formatNumber(stats.high_priority)}
        context="Score band high"
        icon={Waves}
        delay={0.1}
      />
      <KpiCard
        label="Critical priority"
        value={formatNumber(stats.critical_priority)}
        context="Score band critical"
        icon={TriangleAlert}
        tone={stats.critical_priority > 0 ? "critical" : "default"}
        delay={0.14}
      />
      <KpiCard
        label="Deduplicated last run"
        value={stats.last_run_deduplicated == null ? "—" : formatNumber(stats.last_run_deduplicated)}
        context="Repeat conditions suppressed"
        icon={ClipboardList}
        delay={0.18}
      />
    </div>
  );
}
