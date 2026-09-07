import { STATUS_LABELS } from "../../lib/incidents";
import type { IncidentStatus } from "../../types/incidents";
import { Badge } from "../ui/Badge";

const styles: Record<IncidentStatus, string> = {
  investigating: "bg-[#eef6fb] text-navy",
  awaiting_approval: "bg-warning/10 text-warning",
  resolved: "bg-success/10 text-success",
};

interface StatusBadgeProps {
  status: IncidentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <Badge className={styles[status]}>{STATUS_LABELS[status]}</Badge>;
}
