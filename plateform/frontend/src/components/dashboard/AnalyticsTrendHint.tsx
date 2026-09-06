import { useEffect, useState } from "react";

import { fetchAnalyticsOverview } from "../../api/analytics";
import { formatComparison, formatMetricValue } from "../../lib/analytics";

export function AnalyticsTrendHint() {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetchAnalyticsOverview({ range: "24h", zone: "", sensor: "" }, { signal: controller.signal })
      .then((payload) => {
        const pressure = payload.kpis.find((item) => item.key === "average_pressure");
        if (!pressure) {
          return;
        }
        setLabel(`${formatMetricValue(pressure, 2)} · ${formatComparison(pressure)}`);
      })
      .catch(() => {
        setLabel(null);
      });
    return () => controller.abort();
  }, []);

  if (!label) {
    return null;
  }

  return <span title="Simulated 24-hour average pressure from Analytics">24h pressure {label}</span>;
}
