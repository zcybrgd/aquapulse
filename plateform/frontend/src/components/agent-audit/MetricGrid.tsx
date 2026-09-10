import type { ReactNode } from "react";

export function MetricGrid({ children }: { children: ReactNode }) {
  return <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 xl:grid-cols-3">{children}</dl>;
}

export function MetricItem({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-ink-muted" title={hint} aria-label={hint ?? label}>
        {label}
      </dt>
      <dd className="mt-0.5 break-words font-medium text-ink">{value}</dd>
    </div>
  );
}
