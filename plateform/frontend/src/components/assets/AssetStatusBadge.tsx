import { CircleAlert, Radio, WifiOff } from "lucide-react";

import { OPERATIONAL_STATUS_LABELS } from "../../lib/assets";
import type { OperationalStatus } from "../../types/assets";
import { Badge } from "../ui/Badge";

const styles: Record<OperationalStatus, string> = {
  online: "bg-success/10 text-success",
  degraded: "bg-warning/10 text-warning",
  offline: "bg-critical/10 text-critical",
};

const icons = {
  online: Radio,
  degraded: CircleAlert,
  offline: WifiOff,
};

interface AssetStatusBadgeProps {
  status: OperationalStatus;
}

export function AssetStatusBadge({ status }: AssetStatusBadgeProps) {
  const Icon = icons[status];
  return (
    <Badge className={styles[status]}>
      <Icon size={12} aria-hidden="true" />
      {OPERATIONAL_STATUS_LABELS[status]}
    </Badge>
  );
}
