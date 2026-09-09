import { Link } from "react-router-dom";

import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { useIncidentAgentRecommendations } from "../../hooks/useIncidentAgentRecommendations";

interface ResponseRecommendationPanelProps {
  incidentNumber: string;
}

export function ResponseRecommendationPanel({ incidentNumber }: ResponseRecommendationPanelProps) {
  const { runs, loading } = useIncidentAgentRecommendations(incidentNumber);

  if (loading || runs.length === 0) {
    return null;
  }

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Response Agent recommendation</h3>
      <ul className="mt-3 space-y-3">
        {runs.map((run) => (
          <li key={run.id} className="rounded-2xl bg-page px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={run.decision === "AUTONOMOUS_ISOLATE" ? "bg-critical/10 text-critical" : "bg-teal-light text-teal"}>
                {run.decision ?? "—"}
              </Badge>
              <span className="text-xs text-ink-muted">Advisory · unverified</span>
            </div>
            <p className="mt-2 text-sm text-ink-muted">
              AquaPulse does not execute a valve command from this recommendation.
            </p>
            <Link
              to={`/agent-audit/runs/${run.public_id}`}
              className="mt-2 inline-block text-sm font-medium text-teal hover:underline"
            >
              View full reasoning trace
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}