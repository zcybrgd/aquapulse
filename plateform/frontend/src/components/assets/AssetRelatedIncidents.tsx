import { Link } from "react-router-dom";

import { CLASSIFICATION_LABELS } from "../../lib/incidents";
import { formatDateTime } from "../../lib/format";
import type { RelatedAssetIncident } from "../../types/assets";
import { SeverityBadge } from "../incidents/SeverityBadge";
import { StatusBadge } from "../incidents/StatusBadge";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";

interface AssetRelatedIncidentsProps {
  incidents: RelatedAssetIncident[];
}

export function AssetRelatedIncidents({ incidents }: AssetRelatedIncidentsProps) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Related incidents</h3>
      <p className="mt-0.5 text-sm text-ink-muted">
        Active and recent investigations linked to this asset.
      </p>
      {incidents.length === 0 ? (
        <div className="mt-3">
          <EmptyState
            title="No linked incidents"
            description="This asset is not currently referenced by an open or recent investigation."
          />
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {incidents.map((incident) => (
            <li key={incident.incident_number}>
              <Link
                to={`/incidents/${encodeURIComponent(incident.incident_number)}`}
                className="block rounded-2xl border border-line p-3 hover:border-teal/40"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-ink">{incident.incident_number}</p>
                  <SeverityBadge severity={incident.severity} />
                  <StatusBadge status={incident.status} />
                </div>
                <p className="mt-1 text-sm text-ink">{incident.title}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {CLASSIFICATION_LABELS[incident.classification]} · Detected{" "}
                  {formatDateTime(incident.detected_at)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
