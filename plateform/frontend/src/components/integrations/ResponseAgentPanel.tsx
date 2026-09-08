import { Link } from "react-router-dom";

import type { AgentRecommendationRecord } from "../../types/integrations";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Skeleton } from "../ui/Skeleton";

export function ResponseAgentPanel({
  items,
  loading,
  error,
  onRetry,
}: {
  items: AgentRecommendationRecord[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Response Agent recommendation</h3>
      <p className="mt-1 text-sm text-ink-muted">Advisory only. AquaPulse does not execute a valve command.</p>
      {loading ? <Skeleton className="mt-4 h-20 w-full" /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={onRetry} /> : null}
      {!loading && !error && items.length === 0 ? (
        <div className="mt-3">
          <EmptyState
            title="No Response Agent recommendation available"
            description="Waiting for integration. A recommendation appears after a validated Response Agent POST."
          />
        </div>
      ) : null}
      {!loading && !error
        ? items.map((item) => (
            <div key={item.id} className="mt-3 rounded-2xl bg-page px-4 py-3 text-sm">
              <p className="font-medium text-ink">{item.decision}</p>
              <p className="mt-1 text-ink-muted">
                Safety {item.safety_status} · reachability unverified · notification{" "}
                {item.notification_sent ? "reported sent" : "not sent"}
              </p>
              <p className="mt-1 text-ink-muted">
                Valve command {item.valve_command_verified ? "verified" : "unverified"}
              </p>
              <Link
                to={`/integrations/recommendations/${item.id}`}
                className="mt-2 inline-block font-medium text-teal hover:underline"
              >
                Open recommendation
              </Link>
            </div>
          ))
        : null}
    </Card>
  );
}
