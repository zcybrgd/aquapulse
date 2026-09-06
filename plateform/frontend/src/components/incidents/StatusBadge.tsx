import { STATUS_LABELS } from "../../lib/incidents";
import type { IncidentStatus } from "../../types/incidents";
import { Badge } from "../ui/Badge";

const styles: Record<IncidentStatus, string> = {
  open: "bg-page text-ink",
  acknowledged: "bg-[#eef6fb] text-navy",
  investigating: "bg-[#eef6fb] text-navy",
  awaiting_approval: "bg-warning/10 text-warning",
  responding: "bg-teal-light text-teal",
  monitoring: "bg-teal-light text-teal",
  resolved: "bg-success/10 text-success",
  false_alarm: "bg-page text-ink-muted",
};

interface StatusBadgeProps {
  status: IncidentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <Badge className={styles[status]}>{STATUS_LABELS[status]}</Badge>;
}
