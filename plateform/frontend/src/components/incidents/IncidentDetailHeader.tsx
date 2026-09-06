import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { CLASSIFICATION_LABELS } from "../../lib/incidents";
import { formatDateTime } from "../../lib/format";
import type { IncidentDetail } from "../../types/incidents";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";

interface IncidentDetailHeaderProps {
  incident: IncidentDetail;
}

export function IncidentDetailHeader({ incident }: IncidentDetailHeaderProps) {
  const location = useLocation();

  return (
    <div className="min-w-0">
      <Link
        to={`/incidents${location.search}`}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-teal hover:underline"
      >
        <ArrowLeft size={16} aria-hidden="true" />
        Back to Incident Center
      </Link>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-teal">{incident.incident_number}</p>
        <SeverityBadge severity={incident.severity} />
        <StatusBadge status={incident.status} />
        <span className="text-sm text-ink-muted">
          {CLASSIFICATION_LABELS[incident.classification]}
        </span>
      </div>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">{incident.title}</h2>
      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-muted">
        <div>
          <dt className="inline">Detected </dt>
          <dd className="inline text-ink">{formatDateTime(incident.detected_at)}</dd>
        </div>
        <div>
          <dt className="inline">Updated </dt>
          <dd className="inline text-ink">{formatDateTime(incident.updated_at)}</dd>
        </div>
        <div>
          <dt className="inline">Assigned to </dt>
          <dd className="inline text-ink">{incident.assigned_operator ?? "Unassigned"}</dd>
        </div>
      </dl>
    </div>
  );
}
