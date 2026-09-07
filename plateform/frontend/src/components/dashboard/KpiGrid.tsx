import { Activity, Radio, Timer, TriangleAlert } from "lucide-react";

import type { DashboardSummary } from "../../types/api";
import { formatNumber, formatPercent } from "../../lib/format";
import { KpiCard } from "./KpiCard";

interface KpiGridProps {
  summary: DashboardSummary;
}

export function KpiGrid({ summary }: KpiGridProps) {
  const offlineSensors = summary.total_sensors - summary.online_sensors;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <KpiCard
        label="Active incidents"
        value={formatNumber(summary.active_incidents)}
        context={`${summary.critical_incidents} critical · ${summary.awaiting_approval ?? 0} waiting for approval · ${summary.responding ?? 0} response in progress`}
        icon={TriangleAlert}
        tone={summary.critical_incidents > 0 ? "critical" : "default"}
        delay={0.02}
      />
      <KpiCard
        label="Sensors online"
        value={`${formatNumber(summary.online_sensors)}/${formatNumber(summary.total_sensors)}`}
        context={`${offlineSensors} sensors offline`}
        icon={Radio}
        delay={0.06}
      />
      <KpiCard
        label="Network health"
        value={formatPercent(summary.network_health_percent)}
        context="Within operating range"
        icon={Activity}
        delay={0.1}
      />
      <KpiCard
        label="Average response time"
        value={`${formatNumber(summary.average_response_time_min, 1)} min`}
        context="Target under 15 min"
        icon={Timer}
        delay={0.14}
      />
    </div>
  );
}
