import { motion, useReducedMotion } from "framer-motion";

import { Card } from "../ui/Card";

export function NetworkMapPlaceholder() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: 0.22, ease: "easeOut" }}
    >
      <Card className="min-w-0 overflow-hidden p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-ink">Live network preview</h3>
            <p className="mt-0.5 text-sm text-ink-muted">Schematic of pipelines, sensors, and one active incident</p>
          </div>
          <span className="rounded-full bg-teal-light px-2.5 py-1 text-[11px] font-medium text-teal">
            Placeholder
          </span>
        </div>

        <div className="relative overflow-hidden rounded-2xl border border-line bg-aqua-light">
          <svg
            viewBox="0 0 640 280"
            className="block h-56 w-full sm:h-64"
            role="img"
            aria-label="Live network preview showing pipeline lines, sensor nodes, and one highlighted incident"
          >
            <rect width="640" height="280" fill="#E8F8F7" />
            <path
              d="M40 210 C140 210 160 120 260 120 H410 C500 120 520 70 600 70"
              fill="none"
              stroke="#0B2436"
              strokeWidth="3.5"
              strokeLinecap="round"
            />
            <path
              d="M90 40 V150 C90 180 140 190 190 190 H360 C430 190 450 240 560 240"
              fill="none"
              stroke="#08A6A6"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d="M260 120 V190"
              fill="none"
              stroke="#08A6A6"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <circle cx="90" cy="40" r="6" fill="#FFFFFF" stroke="#08A6A6" strokeWidth="2" />
            <circle cx="190" cy="190" r="6" fill="#FFFFFF" stroke="#08A6A6" strokeWidth="2" />
            <circle cx="260" cy="120" r="6" fill="#FFFFFF" stroke="#0B2436" strokeWidth="2" />
            <circle cx="360" cy="190" r="6" fill="#FFFFFF" stroke="#08A6A6" strokeWidth="2" />
            <circle cx="410" cy="120" r="6" fill="#FFFFFF" stroke="#0B2436" strokeWidth="2" />
            <circle cx="560" cy="240" r="6" fill="#FFFFFF" stroke="#08A6A6" strokeWidth="2" />
            <circle cx="410" cy="120" r="14" fill="none" stroke="#E5484D" strokeWidth="2" />
            <circle cx="410" cy="120" r="5" fill="#E5484D" />
            <rect x="428" y="88" width="132" height="36" rx="8" fill="#FFFFFF" />
            <text x="440" y="110" fill="#142B38" fontSize="11" fontFamily="DM Sans, sans-serif">
              Harbour leak · INC-1842
            </text>
          </svg>
        </div>
      </Card>
    </motion.div>
  );
}
