import { CircleAlert, Cpu, Radio, TriangleAlert, WifiOff } from "lucide-react";

import { formatNumber } from "../../lib/format";
import type { AssetListSummary } from "../../types/assets";
import { KpiCard } from "../dashboard/KpiCard";

interface AssetSummaryCardsProps {
  summary: AssetListSummary;
}

export function AssetSummaryCards({ summary }: AssetSummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <KpiCard
        label="Total assets"
        value={formatNumber(summary.total_assets)}
        context="Sensors, valves and gateways"
        icon={Cpu}
        delay={0.02}
      />
      <KpiCard
        label="Online"
        value={formatNumber(summary.online)}
        context="Reporting normally"
        icon={Radio}
        delay={0.06}
      />
      <KpiCard
        label="Degraded"
        value={formatNumber(summary.degraded)}
        context="Connectivity or integrity issues"
        icon={CircleAlert}
        tone={summary.degraded > 0 ? "warning" : "default"}
        delay={0.1}
      />
      <KpiCard
        label="Offline"
        value={formatNumber(summary.offline)}
        context="Not reporting"
        icon={WifiOff}
        tone={summary.offline > 0 ? "critical" : "default"}
        delay={0.14}
      />
      <KpiCard
        label="Maintenance due"
        value={formatNumber(summary.maintenance_due)}
        context="Next visit is overdue"
        icon={TriangleAlert}
        tone={summary.maintenance_due > 0 ? "warning" : "default"}
        delay={0.18}
      />
    </div>
  );
}
