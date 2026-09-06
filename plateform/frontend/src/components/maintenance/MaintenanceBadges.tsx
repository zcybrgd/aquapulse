import { AlertTriangle, Ban, CheckCircle2, Clock3, Play, UserCheck } from "lucide-react";

import { PRIORITY_LABELS, STATUS_LABELS } from "../../lib/maintenance";
import type { MaintenancePriority, WorkOrderStatus } from "../../types/maintenance";
import { Badge } from "../ui/Badge";

const statusStyles: Record<WorkOrderStatus, string> = {
  scheduled: "bg-page text-ink",
  assigned: "bg-teal-light text-teal",
  in_progress: "bg-warning/10 text-warning",
  completed: "bg-success/10 text-success",
  cancelled: "bg-line text-ink-muted",
};

const statusIcons = {
  scheduled: Clock3,
  assigned: UserCheck,
  in_progress: Play,
  completed: CheckCircle2,
  cancelled: Ban,
};

const priorityStyles: Record<MaintenancePriority, string> = {
  low: "bg-page text-ink-muted",
  medium: "bg-teal-light text-navy",
  high: "bg-warning/10 text-warning",
  critical: "bg-critical/10 text-critical",
};

export function WorkOrderStatusBadge({ status }: { status: WorkOrderStatus }) {
  const Icon = statusIcons[status];
  return (
    <Badge className={statusStyles[status]}>
      <Icon size={12} aria-hidden="true" />
      {STATUS_LABELS[status]}
    </Badge>
  );
}

export function MaintenancePriorityBadge({ priority }: { priority: MaintenancePriority }) {
  return (
    <Badge className={priorityStyles[priority]}>
      {priority === "critical" || priority === "high" ? <AlertTriangle size={12} aria-hidden="true" /> : null}
      {PRIORITY_LABELS[priority]}
    </Badge>
  );
}

export function OverdueBadge() {
  return (
    <Badge className="bg-critical/10 text-critical">
      <AlertTriangle size={12} aria-hidden="true" />
      Overdue
    </Badge>
  );
}
