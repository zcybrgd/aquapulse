type StatusTone = "success" | "warning" | "critical";

interface StatusDotProps {
  tone?: StatusTone;
  label: string;
}

const toneClasses: Record<StatusTone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  critical: "bg-critical",
};

export function StatusDot({ tone = "success", label }: StatusDotProps) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-muted">
      <span className={`h-2 w-2 rounded-full ${toneClasses[tone]}`} aria-hidden="true" />
      {label}
    </span>
  );
}
