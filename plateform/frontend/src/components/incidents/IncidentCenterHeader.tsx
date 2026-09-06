import { Link } from "react-router-dom";
import { StatusDot } from "../ui/StatusDot";
import type { IncidentCenterStats } from "../../types/incidents";

interface IncidentCenterHeaderProps {
  stats: IncidentCenterStats;
  ready?: boolean;
}

export function IncidentCenterHeader({ stats, ready = true }: IncidentCenterHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">Incident Center</h2>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Review, filter and open investigations across the water network. Values on this page
          come from the incident service. Coordinate active work in the{" "}
          <Link to="/operations" className="font-medium text-teal hover:underline">
            Operations Center
          </Link>
          . Detections stay in a separate{" "}
          <Link to="/detections" className="font-medium text-teal hover:underline">
            Investigation Queue
          </Link>
          .
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p className="text-ink-muted">
          <span className="font-semibold text-ink">{ready ? stats.active : "—"}</span> active
        </p>
        <StatusDot label="Live monitoring" />
      </div>
    </div>
  );
}
