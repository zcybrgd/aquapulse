import type { LucideIcon } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

interface KpiCardProps {
  label: string;
  value: string;
  context: string;
  icon: LucideIcon;
  delay?: number;
  tone?: "default" | "critical" | "warning";
}

export function KpiCard({
  label,
  value,
  context,
  icon: Icon,
  delay = 0,
  tone = "default",
}: KpiCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.article
      className="card min-w-0 p-5"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay, ease: "easeOut" }}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-ink-muted">{label}</p>
        <span
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
            tone === "critical"
              ? "bg-critical/10 text-critical"
              : tone === "warning"
                ? "bg-warning/10 text-warning"
                : "bg-teal-light text-teal"
          }`}
        >
          <Icon size={18} aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 truncate text-2xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink-muted">{context}</p>
    </motion.article>
  );
}
