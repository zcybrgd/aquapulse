import { DashboardHeader } from "../components/dashboard/DashboardHeader";
import { DashboardSkeleton } from "../components/dashboard/DashboardSkeleton";
import { DetectionPreview } from "../components/dashboard/DetectionPreview";
import { IncidentPreview } from "../components/dashboard/IncidentPreview";
import { KpiGrid } from "../components/dashboard/KpiGrid";
import { NetworkHealthPanel } from "../components/dashboard/NetworkHealthPanel";
import { NetworkMapPreview } from "../components/dashboard/NetworkMapPreview";
import { TelemetryChart } from "../components/dashboard/TelemetryChart";
import { ErrorState } from "../components/ui/ErrorState";
import { useDashboardData } from "../hooks/useDashboardData";

export function OverviewPage() {
  const {
    summary,
    telemetry,
    telemetryMeta,
    range,
    setRange,
    loading,
    refreshing,
    error,
    backgroundError,
    lastRefreshAt,
    reload,
  } = useDashboardData();

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
      <DashboardHeader
        lastRefreshAt={lastRefreshAt}
        refreshing={refreshing}
        backgroundError={backgroundError}
        lastUpdated={telemetryMeta?.last_updated ?? null}
        onRefresh={reload}
      />

      {loading ? <DashboardSkeleton /> : null}

      {!loading && error ? (
        <ErrorState title="Unable to load telemetry" message={error} onRetry={reload} />
      ) : null}

      {!loading && !error && summary ? (
        <>
          <KpiGrid summary={summary} />
          <DetectionPreview />
          <TelemetryChart readings={telemetry} range={range} onRangeChange={setRange} />
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <IncidentPreview />
            <NetworkHealthPanel summary={summary} telemetry={telemetry} />
          </div>
          <NetworkMapPreview />
        </>
      ) : null}
    </div>
  );
}
