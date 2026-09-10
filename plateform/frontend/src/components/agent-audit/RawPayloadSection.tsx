import { useState } from "react";

import { formatOptionalText } from "../../lib/agentAuditDisplay";
import type { JsonValue } from "../../types/agentAudit";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

interface RawPayloadSectionProps {
  payload: JsonValue;
}

export function RawPayloadSection({ payload }: RawPayloadSectionProps) {
  const [copied, setCopied] = useState(false);
  const serialized = payload === null ? "" : JSON.stringify(payload, null, 2);

  async function copyJson() {
    if (!serialized) return;
    try {
      await navigator.clipboard.writeText(serialized);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Card className="min-w-0 p-5">
      <details className="group" data-testid="raw-payload">
        <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal [&::-webkit-details-marker]:hidden">
          <div>
            <h3 className="text-base font-semibold text-ink">Technical details — raw sanitized payload</h3>
            <p className="mt-1 text-sm text-ink-muted">For developers. Collapsed by default.</p>
          </div>
          <span className="text-sm font-medium text-teal group-open:hidden">Expand</span>
          <span className="hidden text-sm font-medium text-teal group-open:inline">Collapse</span>
        </summary>
        <div className="mt-4 min-w-0">
          <div className="mb-3">
            <Button variant="secondary" onClick={() => void copyJson()} disabled={!serialized}>
              {copied ? "Copied" : "Copy JSON"}
            </Button>
          </div>
          {serialized ? (
            <pre className="max-h-96 overflow-auto rounded-xl bg-page p-3 text-xs text-ink">
              {serialized}
            </pre>
          ) : (
            <p className="text-sm text-ink-muted">{formatOptionalText(null)}</p>
          )}
        </div>
      </details>
    </Card>
  );
}
