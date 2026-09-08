import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

import { formatDateTime } from "../../lib/format";
import { scorePercent } from "../../lib/detections";
import { useAgentFindings } from "../../hooks/useAgentFindings";
import { useDetectionPreview } from "../../hooks/useDetections";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Skeleton } from "../ui/Skeleton";
import { Button } from "../ui/Button";
import { DetectionPriorityBadge } from "../detections/DetectionPriorityBadge";
import { DetectionStatusBadge } from "../detections/DetectionStatusBadge";

export function DetectionPreview() {
  const { stats, loading, error, reload } = useDetectionPreview();
  const findings = useAgentFindings();
  const reduceMotion = useReducedMotion();
  const preview = stats?.highest_priority ?? null;
  const awaiting = (stats?.new ?? 0) + (stats?.queued ?? 0);

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: 0.1, ease: "easeOut" }}
    >
      <Card className="min-w-0 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-ink">Investigation queue</h3>
            <p className="mt-0.5 text-sm text-ink-muted">
              {loading
                ? "Loading detections"
                : findings.items.length > 0
                  ? `${findings.items.length} Investigation Agent results`
                  : `${awaiting} screening detections · Awaiting Investigation Agent result`}
            </p>
          </div>
          <Link
            to="/detections"
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm font-medium text-teal hover:bg-teal-light"
          >
            Open Investigation Queue
            <ArrowUpRight size={14} aria-hidden="true" />
          </Link>
        </div>

        {loading ? <Skeleton className="h-20 w-full" /> : null}
        {!loading && error ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-ink-muted">{error}</p>
            <Button variant="secondary" onClick={reload}>
              Try again
            </Button>
          </div>
        ) : null}
        {!loading && !error && !preview ? (
          <EmptyState
            title="No detections in the queue"
            description="Deterministic rules have not flagged suspicious telemetry. Detections are not confirmed incidents."
          />
        ) : null}
        {!loading && !error && preview ? (
          <div className="rounded-2xl border border-line px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <DetectionPriorityBadge priority={preview.priority} />
              <DetectionStatusBadge status={preview.status} />
              <span className="text-sm font-medium text-ink">{preview.detection_number}</span>
            </div>
            <p className="mt-2 text-sm text-ink">{preview.trigger_reason}</p>
            <p className="mt-1 text-xs text-ink-muted">
              {preview.sensor_id} · {preview.zone} · score {scorePercent(preview.anomaly_score)} ·{" "}
              {formatDateTime(preview.detected_at)}
            </p>
          </div>
        ) : null}
      </Card>
    </motion.div>
  );
}
