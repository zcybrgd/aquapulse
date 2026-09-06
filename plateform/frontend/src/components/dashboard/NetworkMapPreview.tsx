import { lazy, Suspense } from "react";
import { motion, useReducedMotion } from "framer-motion";

import { Card } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

const FocusedMap = lazy(() => import("../map/FocusedMap"));

export function NetworkMapPreview() {
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
            <p className="mt-0.5 text-sm text-ink-muted">
              Seeded pipelines, assets and active incidents from PostGIS
            </p>
          </div>
          <span className="rounded-full bg-teal-light px-2.5 py-1 text-[11px] font-medium text-teal">
            Seeded demo
          </span>
        </div>
        <Suspense fallback={<Skeleton className="h-56 w-full rounded-2xl" />}>
          <FocusedMap variant="overview" />
        </Suspense>
      </Card>
    </motion.div>
  );
}
