import type { ReactNode } from "react";

interface TermTooltipProps {
  term: string;
  children: ReactNode;
}

export function TermTooltip({ term, children }: TermTooltipProps) {
  return (
    <span className="cursor-help border-b border-dotted border-ink-muted" title={term} aria-label={term}>
      {children}
    </span>
  );
}
