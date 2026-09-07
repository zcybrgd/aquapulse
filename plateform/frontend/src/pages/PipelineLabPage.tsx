import { useEffect, useState } from "react";

import { TESTBED_DASHBOARD_URL } from "../lib/testbed";

export function PipelineLabPage() {
  const [status, setStatus] = useState<"checking" | "ready" | "offline">("checking");

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 4000);
    fetch("/pipeline-lab-proxy/api/state", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("unavailable");
        setStatus("ready");
      })
      .catch(() => setStatus("offline"))
      .finally(() => window.clearTimeout(timer));
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <div className="flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden bg-page">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-line bg-white px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">Pipeline Lab</p>
          <p className="text-xs text-ink-muted">
            Water-pipeline testbed digital twin. This is a physics simulator, not AquaPulse live operations.
          </p>
        </div>
        <p className="text-xs font-medium text-ink-muted">
          {status === "checking" ? "Checking testbed…" : null}
          {status === "ready" ? "Connected to testbed dashboard" : null}
          {status === "offline" ? "Testbed dashboard is not running" : null}
        </p>
      </div>

      {status === "offline" ? (
        <div className="shrink-0 border-b border-warning/30 bg-warning/10 px-4 py-3 text-sm text-ink sm:px-5">
          The testbed dashboard did not answer on {TESTBED_DASHBOARD_URL}. Start it with{" "}
          <code className="rounded bg-white px-1.5 py-0.5 text-xs">
            docker compose -f docker-compose.yml -f docker-compose.plateform.yml up --build
          </code>{" "}
          from <code className="text-xs">aquapulse/water-pipeline-testbed</code>. Simulator host
          port is 8002 so it does not collide with the AquaPulse API.
        </div>
      ) : null}

      <iframe
        title="Water pipeline testbed"
        src={TESTBED_DASHBOARD_URL}
        className="h-full min-h-0 w-full flex-1 border-0 bg-[#0b1220]"
        allow="fullscreen"
      />
    </div>
  );
}
