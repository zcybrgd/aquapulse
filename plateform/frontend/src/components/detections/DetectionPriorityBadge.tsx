import { Badge } from "../ui/Badge";
import type { DetectionPriority } from "../../types/detections";
import { PRIORITY_LABELS } from "../../lib/detections";

const styles: Record<DetectionPriority, string> = {
  low: "bg-page text-ink-muted",
  medium: "bg-teal-light text-teal",
  high: "bg-warning/10 text-warning",
  critical: "bg-critical/10 text-critical",
};

export function DetectionPriorityBadge({
  priority,
  screening = true,
}: {
  priority: DetectionPriority;
  screening?: boolean;
}) {
  return (
    <Badge className={styles[priority]}>
      {screening ? `Screening priority · ${PRIORITY_LABELS[priority]}` : PRIORITY_LABELS[priority]}
    </Badge>
  );
}
