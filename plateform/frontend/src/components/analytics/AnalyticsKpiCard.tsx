import { Info } from "lucide-react";
import { Link } from "react-router-dom";

import { formatComparison, formatMetricValue, KPI_TOOLTIPS, trendTone } from "../../lib/analytics";
import type { ComparedMetric } from "../../types/analytics";
import { Card } from "../ui/Card";

interface AnalyticsKpiCardProps {
  metric?: ComparedMetric;
  href?: string;
  digits?: number;
}

export function AnalyticsKpiCard({ metric, href, digits = 1 }: AnalyticsKpiCardProps) {
  if (!metric) {
    return (
      <Card className="min-w-0 p-4">
        <p className="text-sm text-ink-muted">Unavailable</p>
      </Card>
    );
  }
  const tooltip = KPI_TOOLTIPS[metric.key] ?? metric.label;
  const tone = trendTone(metric.trend, metric.interpretation);
  const toneClass =
    tone === "up" ? "text-teal" : tone === "down" ? "text-critical" : "text-ink-muted";
  const content = (
    <>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{metric.label}</p>
        <span className="text-ink-muted" title={tooltip} aria-label={tooltip}>
          <Info size={14} aria-hidden="true" />
        </span>
      </div>
      <p className="mt-2 truncate text-2xl font-semibold text-ink">{formatMetricValue(metric, digits)}</p>
      <p className={`mt-1 text-sm ${toneClass}`}>{formatComparison(metric)}</p>
    </>
  );

  if (href) {
    return (
      <Card className="min-w-0 p-4">
        <Link to={href} className="block min-w-0 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal">
          {content}
        </Link>
      </Card>
    );
  }

  return <Card className="min-w-0 p-4">{content}</Card>;
}
