import { Badge } from "../ui/Badge";
import { statusLabel } from "../../lib/agentAuditDisplay";

const TONE: Record<string, string> = {
  succeeded: "bg-success/15 text-success",
  failed: "bg-critical/10 text-critical",
  rejected: "bg-critical/10 text-critical",
  cancelled: "bg-page text-ink-muted",
  running: "bg-teal-light text-teal",
  pending: "bg-page text-ink",
  validating: "bg-warning/15 text-ink",
  ready: "bg-teal-light text-teal",
  blocked: "bg-critical/10 text-critical",
  advisory: "bg-teal-light text-teal",
  agent_reported_unverified: "bg-warning/15 text-ink",
  mapped: "bg-teal-light text-teal",
  unmapped: "bg-warning/15 text-ink",
  partial: "bg-warning/15 text-ink",
  confirmed_anomaly: "bg-critical/10 text-critical",
  confirmed_instrument_fault: "bg-page text-ink",
};

interface AuditStatusBadgeProps {
  value: string;
  label?: string;
}

export function AuditStatusBadge({ value, label }: AuditStatusBadgeProps) {
  return (
    <Badge className={TONE[value] ?? "bg-page text-ink"} aria-label={label ?? statusLabel(value)}>
      {label ?? statusLabel(value)}
    </Badge>
  );
}
