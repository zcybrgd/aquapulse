import { AlertTriangle, CircleAlert, Droplets } from "lucide-react";

import { SEVERITY_LABELS } from "../../lib/incidents";
import type { SeverityTier } from "../../types/incidents";
import { Badge } from "../ui/Badge";

const styles: Record<SeverityTier, string> = {
  tier_1: "bg-teal-light text-teal",
  tier_2: "bg-warning/10 text-warning",
  tier_3: "bg-critical/10 text-critical",
};

const icons = {
  tier_1: Droplets,
  tier_2: AlertTriangle,
  tier_3: CircleAlert,
} as const;

interface SeverityBadgeProps {
  severity: SeverityTier;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const Icon = icons[severity];

  return (
    <Badge className={styles[severity]}>
      <Icon size={12} aria-hidden="true" />
      <span>{SEVERITY_LABELS[severity]}</span>
    </Badge>
  );
}
