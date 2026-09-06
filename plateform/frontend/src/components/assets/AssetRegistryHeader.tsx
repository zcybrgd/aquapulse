import { StatusDot } from "../ui/StatusDot";
import { Badge } from "../ui/Badge";
import type { AssetListSummary } from "../../types/assets";
import { formatNumber } from "../../lib/format";

interface AssetRegistryHeaderProps {
  summary: AssetListSummary;
  lastSeen: string | null;
  ready?: boolean;
}

export function AssetRegistryHeader({ summary, lastSeen, ready = true }: AssetRegistryHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">Asset Registry</h2>
          <Badge className="bg-page text-ink-muted">Read-only</Badge>
        </div>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Inventory of sensors, valves and gateways used in the demo utility. This register does
          not represent live field infrastructure, and changes are disabled until authentication
          exists.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p className="text-ink-muted">
          <span className="font-semibold text-ink">{ready ? formatNumber(summary.total_assets) : "—"}</span>{" "}
          assets
        </p>
        <StatusDot label={ready && lastSeen ? `Synced ${lastSeen}` : "Demo inventory"} />
      </div>
    </div>
  );
}
