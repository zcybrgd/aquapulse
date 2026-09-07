import { Badge } from "../ui/Badge";
import type { ReachabilityStatus, SourceMode } from "../../types/networkHealth";

const REACHABILITY_STYLES: Record<ReachabilityStatus, string> = {
  reachable: "bg-teal-light text-teal",
  unreachable: "bg-critical/10 text-critical",
  unknown: "bg-warning/15 text-ink",
  not_supported: "bg-page text-ink-muted",
  not_checked: "bg-page text-ink-muted",
};

const REACHABILITY_LABELS: Record<ReachabilityStatus, string> = {
  reachable: "Reachable",
  unreachable: "Unreachable",
  unknown: "Unknown",
  not_supported: "No SIM",
  not_checked: "Not checked",
};

const SOURCE_STYLES: Record<SourceMode, string> = {
  seeded_demo: "bg-page text-ink",
  nokia_simulator: "bg-warning/15 text-ink",
  nokia_live: "bg-teal-light text-teal",
};

export function ReachabilityBadge({ status }: { status: ReachabilityStatus }) {
  return <Badge className={REACHABILITY_STYLES[status]}>{REACHABILITY_LABELS[status]}</Badge>;
}

export function SourceModeBadge({
  mode,
  label,
}: {
  mode: SourceMode | null | undefined;
  label?: string;
}) {
  if (!mode) {
    return <Badge className="bg-page text-ink-muted">{label ?? "No snapshot"}</Badge>;
  }
  return <Badge className={SOURCE_STYLES[mode]}>{label ?? sourceModeLabel(mode)}</Badge>;
}

export function sourceModeLabel(mode: SourceMode): string {
  if (mode === "nokia_live") return "Nokia live";
  if (mode === "nokia_simulator") return "Nokia simulator";
  return "Demonstration data";
}

export function reachabilityLabel(status: ReachabilityStatus): string {
  return REACHABILITY_LABELS[status];
}
