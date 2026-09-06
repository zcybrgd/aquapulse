import { Link } from "react-router-dom";

import { Card } from "../ui/Card";

export function IncidentActions() {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Related work</h3>
      <p className="mt-1 text-sm text-ink-muted">
        Operational status, tasks and acknowledgements are in the Operations panel. Seeded incidents
        are not auto-linked to detections.
      </p>
      <div className="mt-4 flex flex-col gap-2">
        <Link to="/operations" className="text-sm font-medium text-teal hover:underline">
          Open Operations Center
        </Link>
        <Link to="/maintenance" className="text-sm font-medium text-teal hover:underline">
          Open Maintenance Center
        </Link>
        <Link to="/detections" className="text-sm font-medium text-teal hover:underline">
          Open Investigation Queue
        </Link>
      </div>
    </Card>
  );
}
