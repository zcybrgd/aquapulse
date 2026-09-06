import { Badge } from "../ui/Badge";
import type { DetectionStatus } from "../../types/detections";
import { STATUS_LABELS } from "../../lib/detections";

const styles: Record<DetectionStatus, string> = {
  new: "bg-teal-light text-teal",
  queued: "bg-[#eef6fb] text-navy",
  under_review: "bg-warning/10 text-warning",
  dismissed: "bg-page text-ink-muted",
  promoted: "bg-success/10 text-success",
  merged: "bg-page text-ink-muted",
};

export function DetectionStatusBadge({ status }: { status: DetectionStatus }) {
  return <Badge className={styles[status]}>{STATUS_LABELS[status]}</Badge>;
}
