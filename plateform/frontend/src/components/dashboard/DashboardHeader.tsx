import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

import { StatusDot } from "../ui/StatusDot";
import { formatDisplayDate } from "../../lib/format";
import { TelemetryStatusBar } from "../telemetry/TelemetryStatusBar";
import { AnalyticsTrendHint } from "./AnalyticsTrendHint";

interface DashboardHeaderProps {
  lastRefreshAt: string | null;
  refreshing: boolean;
  backgroundError: string | null;
  lastUpdated: string | null;
  onRefresh: () => void;
}

export function DashboardHeader({
  lastRefreshAt,
  refreshing,
  backgroundError,
  lastUpdated,
  onRefresh,
}: DashboardHeaderProps) {
  const now = new Date();

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-medium text-teal">Network overview</p>
        <h2 className="mt-1 max-w-2xl text-2xl font-semibold tracking-tight text-ink">
          Here is what is happening across your water network
        </h2>
        <div className="mt-3">
          <TelemetryStatusBar
            lastUpdated={lastUpdated}
            lastRefreshAt={lastRefreshAt}
            refreshing={refreshing}
            backgroundError={backgroundError}
            onRefresh={onRefresh}
          />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
        <StatusDot label="Simulated telemetry" />
        <AnalyticsTrendHint />
        <Link
          to="/analytics"
          className="inline-flex items-center gap-1 font-medium text-teal hover:underline"
        >
          View Analytics
          <ArrowUpRight size={14} aria-hidden="true" />
        </Link>
        <span>{formatDisplayDate(now)}</span>
      </div>
    </div>
  );
}
