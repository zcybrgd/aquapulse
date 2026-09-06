import { useEffect, useRef } from "react";

interface UsePollingOptions {
  enabled: boolean;
  intervalMs: number;
  resetKey?: string | number;
  onTick: (signal: AbortSignal) => Promise<void>;
}

export function usePolling({ enabled, intervalMs, resetKey, onTick }: UsePollingOptions): void {
  const onTickRef = useRef(onTick);
  onTickRef.current = onTick;

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let cancelled = false;
    let inFlight = false;
    let timer: number | undefined;
    let controller: AbortController | null = null;

    const run = async () => {
      if (cancelled || inFlight || document.visibilityState === "hidden") {
        return;
      }
      inFlight = true;
      controller?.abort();
      controller = new AbortController();
      try {
        await onTickRef.current(controller.signal);
      } catch {
        /* Callers keep the last successful payload. */
      } finally {
        inFlight = false;
      }
    };

    void run();
    timer = window.setInterval(() => {
      void run();
    }, intervalMs);

    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void run();
      } else {
        controller?.abort();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      controller?.abort();
      if (timer !== undefined) {
        window.clearInterval(timer);
      }
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [enabled, intervalMs, resetKey]);
}
