import { RefreshCw } from "lucide-react";

import { formatDateTime } from "../../lib/format";
import { Button } from "../ui/Button";
import { SimulatedTelemetryBadge } from "./TelemetryBadges";

interface TelemetryStatusBarProps {
  lastUpdated: string | null;
  lastRefreshAt: string | null;
  refreshing: boolean;
  backgroundError: string | null;
  onRefresh: () => void;
}

export function TelemetryStatusBar({
  lastUpdated,
  lastRefreshAt,
  refreshing,
  backgroundError,
  onRefresh,
}: TelemetryStatusBarProps) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-ink-muted">
      <SimulatedTelemetryBadge />
      <span>
        Last reading {lastUpdated ? formatDateTime(lastUpdated) : "unavailable"}
      </span>
      <span>Refreshed {lastRefreshAt ? formatDateTime(lastRefreshAt) : "—"}</span>
      {refreshing ? (
        <span className="text-teal" aria-live="polite">
          Refreshing…
        </span>
      ) : null}
      {backgroundError ? <span className="text-warning">{backgroundError}</span> : null}
      <Button
        variant="secondary"
        className="h-8 px-2.5"
        onClick={onRefresh}
        disabled={refreshing}
        aria-label="Refresh telemetry"
      >
        <RefreshCw size={14} className={refreshing ? "opacity-60" : ""} aria-hidden="true" />
        Refresh
      </Button>
    </div>
  );
}
