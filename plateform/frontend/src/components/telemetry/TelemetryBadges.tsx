import { Badge } from "../ui/Badge";
import type { FreshnessState } from "../../types/telemetry";

const labels: Record<FreshnessState, string> = {
  fresh: "Fresh",
  stale: "Stale",
  offline: "Offline",
};

const classes: Record<FreshnessState, string> = {
  fresh: "bg-teal-light text-teal",
  stale: "bg-warning/15 text-warning",
  offline: "bg-page text-ink-muted",
};

export function FreshnessBadge({ state }: { state: FreshnessState }) {
  return <Badge className={classes[state]}>{labels[state]}</Badge>;
}

export function SimulatedTelemetryBadge() {
  return <Badge className="bg-teal-light text-teal">Simulated telemetry</Badge>;
}
