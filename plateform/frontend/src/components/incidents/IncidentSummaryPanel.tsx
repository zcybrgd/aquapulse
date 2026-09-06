import { CLASSIFICATION_LABELS } from "../../lib/incidents";
import type { IncidentDetail } from "../../types/incidents";
import { Card } from "../ui/Card";

interface IncidentSummaryPanelProps {
  incident: IncidentDetail;
}

export function IncidentSummaryPanel({ incident }: IncidentSummaryPanelProps) {
  const confidence = Math.round(incident.confidence);

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Incident summary</h3>
      <p className="mt-3 text-sm leading-6 text-ink">{incident.current_summary}</p>
      <div className="mt-4 rounded-2xl bg-page px-4 py-3">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          Agent investigation
        </p>
        <p className="mt-1.5 text-sm leading-6 text-ink">{incident.agent_investigation_summary}</p>
      </div>
      <div className="mt-5">
        <div className="flex items-center justify-between gap-3 text-sm">
          <p className="font-medium text-ink">Confidence</p>
          <p className="text-ink-muted">
            {confidence}% · {CLASSIFICATION_LABELS[incident.classification]}
          </p>
        </div>
        <div
          className="mt-2 h-2 rounded-full bg-line"
          role="meter"
          aria-label="Investigation confidence"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={confidence}
        >
          <div
            className="h-2 rounded-full bg-teal"
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>
      <div className="mt-5">
        <p className="text-sm font-medium text-ink">Recommended action</p>
        <p className="mt-1.5 text-sm leading-6 text-ink-muted">{incident.recommended_action}</p>
      </div>
    </Card>
  );
}
