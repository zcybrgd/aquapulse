import { CheckCircle2, Clock3, Search, TriangleAlert, Layers } from "lucide-react";

import { formatNumber } from "../../lib/format";
import type { IncidentCenterStats } from "../../types/incidents";
import { KpiCard } from "../dashboard/KpiCard";

interface IncidentSummaryCardsProps {
  stats: IncidentCenterStats;
}

export function IncidentSummaryCards({ stats }: IncidentSummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <KpiCard
        label="Total incidents"
        value={formatNumber(stats.total)}
        context="All records in the current catalogue"
        icon={Layers}
        delay={0.02}
      />
      <KpiCard
        label="Critical incidents"
        value={formatNumber(stats.critical)}
        context="Tier 3 events"
        icon={TriangleAlert}
        tone={stats.critical > 0 ? "critical" : "default"}
        delay={0.06}
      />
      <KpiCard
        label="Waiting for approval"
        value={formatNumber(stats.awaitingApproval)}
        context="Waiting for operator decision"
        icon={Clock3}
        delay={0.1}
      />
      <KpiCard
        label="Under investigation"
        value={formatNumber(stats.investigating)}
        context="Incidents currently being investigated"
        icon={Search}
        delay={0.14}
      />
      <KpiCard
        label="Resolved today"
        value={formatNumber(stats.resolvedToday)}
        context="Closed during the current day"
        icon={CheckCircle2}
        delay={0.18}
      />
    </div>
  );
}
