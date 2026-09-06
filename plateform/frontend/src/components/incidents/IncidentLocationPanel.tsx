import { lazy, Suspense } from "react";

import { formatNumber } from "../../lib/format";
import type { IncidentDetail } from "../../types/incidents";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

const FocusedMap = lazy(() => import("../map/FocusedMap"));

interface IncidentLocationPanelProps {
  incident: IncidentDetail;
}

export function IncidentLocationPanel({ incident }: IncidentLocationPanelProps) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Location and affected assets</h3>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Zone</dt>
          <dd className="text-right font-medium text-ink">{incident.zone}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Pipeline segment</dt>
          <dd className="text-right font-medium text-ink">{incident.pipeline_segment}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Sensor</dt>
          <dd className="text-right font-medium text-ink">{incident.sensor}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Associated valve</dt>
          <dd className="text-right font-medium text-ink">{incident.associated_valve}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Population affected</dt>
          <dd className="text-right font-medium text-ink">
            {formatNumber(incident.population_affected)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Coordinates</dt>
          <dd className="text-right font-medium text-ink">
            {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
          </dd>
        </div>
      </dl>
      <div className="mt-4">
        <Suspense fallback={<Skeleton className="h-40 w-full rounded-2xl" />}>
          <FocusedMap variant="incident" incident={incident} />
        </Suspense>
      </div>
    </Card>
  );
}
