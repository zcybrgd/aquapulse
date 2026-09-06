import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

import { CLASSIFICATION_LABELS } from "../../lib/incidents";
import { formatDateTime } from "../../lib/format";
import { useIncidentPreview } from "../../hooks/useIncidents";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Skeleton } from "../ui/Skeleton";
import { SeverityBadge } from "../incidents/SeverityBadge";
import { StatusBadge } from "../incidents/StatusBadge";
import { Button } from "../ui/Button";

export function IncidentPreview() {
  const { items, loading, error, reload } = useIncidentPreview();
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: 0.16, ease: "easeOut" }}
    >
      <Card className="min-w-0 p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-ink">Incident preview</h3>
            <p className="mt-0.5 text-sm text-ink-muted">Highest-priority active events</p>
          </div>
          <Link
            to="/operations"
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm font-medium text-teal hover:bg-teal-light"
          >
            Open Operations Center
            <ArrowUpRight size={14} aria-hidden="true" />
          </Link>
        </div>

        {loading ? (
          <div className="space-y-3" aria-busy="true">
            <span className="sr-only">Loading incident preview</span>
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : null}

        {!loading && error ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-ink-muted">{error}</p>
            <Button variant="secondary" onClick={reload}>
              Try again
            </Button>
          </div>
        ) : null}

        {!loading && !error && items.length === 0 ? (
          <EmptyState
            title="No open incidents"
            description="The network is quiet. New events will appear here as they are detected."
          />
        ) : null}

        {!loading && !error && items.length > 0 ? (
          <ul className="space-y-3">
            {items.map((incident) => (
              <li key={incident.id} className="rounded-2xl border border-line px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={incident.severity} />
                      <StatusBadge status={incident.status} />
                    </div>
                    <p className="mt-1.5 truncate text-sm font-medium text-ink">{incident.title}</p>
                    <p className="mt-1 text-sm text-ink-muted">{incident.location}</p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {CLASSIFICATION_LABELS[incident.classification]} · Detected{" "}
                      {formatDateTime(incident.detected_at)}
                    </p>
                  </div>
                  <Link
                    to={`/incidents/${encodeURIComponent(incident.id)}`}
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-sm font-medium text-teal hover:bg-teal-light"
                  >
                    View incident
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </motion.div>
  );
}
