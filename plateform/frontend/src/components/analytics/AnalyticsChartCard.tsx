import type { ReactNode } from "react";
import { useReducedMotion } from "framer-motion";

import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Skeleton } from "../ui/Skeleton";

interface AnalyticsChartCardProps {
  title: string;
  description: string;
  loading?: boolean;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function AnalyticsChartCard({
  title,
  description,
  loading = false,
  empty = false,
  emptyTitle = "No records in this period",
  emptyDescription = "Try another range, zone or sensor. Missing values are left blank instead of shown as zero.",
  actions,
  children,
}: AnalyticsChartCardProps) {
  const reduceMotion = useReducedMotion();
  void reduceMotion;

  return (
    <Card className="min-w-0 p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-ink">{title}</h3>
          <p className="mt-0.5 text-sm text-ink-muted">{description}</p>
        </div>
        {actions}
      </div>
      {loading ? <Skeleton className="h-72 w-full" /> : null}
      {!loading && empty ? <EmptyState title={emptyTitle} description={emptyDescription} /> : null}
      {!loading && !empty ? <div className="h-72 min-w-0">{children}</div> : null}
    </Card>
  );
}
