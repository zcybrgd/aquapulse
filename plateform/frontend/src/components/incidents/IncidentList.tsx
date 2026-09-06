import { Link, useLocation, useNavigate } from "react-router-dom";

import { CLASSIFICATION_LABELS } from "../../lib/incidents";
import { formatDateTime, formatNumber } from "../../lib/format";
import type { IncidentSummary } from "../../types/incidents";
import { Card } from "../ui/Card";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";

interface IncidentListProps {
  items: IncidentSummary[];
}

function detailsPath(id: string, search: string): string {
  return `/incidents/${encodeURIComponent(id)}${search}`;
}

export function IncidentTable({ items }: IncidentListProps) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Card className="hidden min-w-0 overflow-hidden xl:block">
      <table className="w-full table-fixed border-collapse text-left text-sm">
          <thead className="bg-page text-xs font-medium uppercase tracking-wide text-ink-muted">
            <tr>
              <th className="w-[18%] px-4 py-3">Incident</th>
              <th className="w-[11%] px-4 py-3">Severity</th>
              <th className="w-[14%] px-4 py-3">Classification</th>
              <th className="w-[14%] px-4 py-3">Location</th>
              <th className="w-[12%] px-4 py-3">Status</th>
              <th className="w-[10%] px-4 py-3">Detected</th>
              <th className="w-[8%] px-4 py-3">Est. loss</th>
              <th className="w-[8%] px-4 py-3">Assigned to</th>
              <th className="w-[5%] px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((incident) => (
              <tr
                key={incident.id}
                className="cursor-pointer border-t border-line transition-colors hover:bg-teal-light/40"
                onClick={() => navigate(detailsPath(incident.id, location.search))}
              >
                <td className="px-4 py-3 align-top">
                  <p className="font-medium text-ink">{incident.incident_number}</p>
                  <p className="mt-0.5 truncate text-ink-muted">{incident.title}</p>
                </td>
                <td className="px-4 py-3 align-top">
                  <SeverityBadge severity={incident.severity} />
                </td>
                <td className="px-4 py-3 align-top text-ink">
                  {CLASSIFICATION_LABELS[incident.classification]}
                </td>
                <td className="px-4 py-3 align-top">
                  <p className="truncate text-ink">{incident.zone}</p>
                  <p className="mt-0.5 truncate text-xs text-ink-muted">
                    {incident.pipeline_segment}
                  </p>
                </td>
                <td className="px-4 py-3 align-top">
                  <StatusBadge status={incident.status} />
                </td>
                <td className="px-4 py-3 align-top text-ink-muted">
                  {formatDateTime(incident.detected_at)}
                </td>
                <td className="px-4 py-3 align-top text-ink">
                  {formatNumber(incident.estimated_water_loss_m3, 1)} m³
                </td>
                <td className="px-4 py-3 align-top text-ink-muted">
                  {incident.assigned_operator ?? "Unassigned"}
                </td>
                <td className="px-4 py-3 align-top">
                  <Link
                    to={detailsPath(incident.id, location.search)}
                    className="relative z-10 text-sm font-medium text-teal hover:underline"
                    onClick={(event) => event.stopPropagation()}
                  >
                    View details
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
    </Card>
  );
}

export function IncidentCardList({ items }: IncidentListProps) {
  const location = useLocation();

  return (
    <ul className="space-y-3 xl:hidden">
      {items.map((incident) => (
        <li key={incident.id}>
          <Link
            to={detailsPath(incident.id, location.search)}
            className="card block min-w-0 p-4 hover:border-teal/30"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-ink">{incident.incident_number}</p>
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
            </div>
            <p className="mt-2 text-sm font-medium text-ink">{incident.title}</p>
            <p className="mt-1 text-sm text-ink-muted">{incident.location}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-muted">
              <div>
                <dt>Classification</dt>
                <dd className="mt-0.5 text-ink">
                  {CLASSIFICATION_LABELS[incident.classification]}
                </dd>
              </div>
              <div>
                <dt>Detected</dt>
                <dd className="mt-0.5 text-ink">{formatDateTime(incident.detected_at)}</dd>
              </div>
              <div>
                <dt>Estimated loss</dt>
                <dd className="mt-0.5 text-ink">
                  {formatNumber(incident.estimated_water_loss_m3, 1)} m³
                </dd>
              </div>
              <div>
                <dt>Assigned to</dt>
                <dd className="mt-0.5 text-ink">{incident.assigned_operator ?? "Unassigned"}</dd>
              </div>
            </dl>
            <p className="mt-3 text-sm font-medium text-teal">View details</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
