import { RefreshCw } from "lucide-react";

import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { formatDateTime } from "../../lib/format";
import {
  CONNECTIVITY_BADGE_CLASS,
  EXECUTION_BADGE_CLASS,
  connectivityLabel,
  connectivityTone,
  contractLabel,
  executionLabel,
} from "../../lib/integrationStatus";
import type { AgentRuntimeStatus } from "../../types/integrations";

interface AgentStatusCardProps {
  agent: AgentRuntimeStatus;
  checking?: boolean;
  onCheckAgain?: () => void;
}

export function AgentStatusCard({ agent, checking = false, onCheckAgain }: AgentStatusCardProps) {
  const tone = connectivityTone(agent);
  const connectedLabel = connectivityLabel(agent);

  return (
    <Card className="min-w-0 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink">{agent.display_name}</h3>
          <p className="mt-1 text-sm text-ink-muted">{agent.agent_type}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Badge className={CONNECTIVITY_BADGE_CLASS[tone]}>{connectedLabel}</Badge>
          <Badge className={agent.execution_enabled ? EXECUTION_BADGE_CLASS.enabled : EXECUTION_BADGE_CLASS.disabled}>
            {executionLabel(agent)}
          </Badge>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-ink-muted">Contract status</dt>
          <dd className="font-medium text-ink">{contractLabel(agent)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Contract version</dt>
          <dd className="font-medium text-ink">{agent.contract_version ?? "Unavailable"}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Last checked</dt>
          <dd className="font-medium text-ink">{formatDateTime(agent.checked_at)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Response time</dt>
          <dd className="font-medium text-ink">
            {agent.response_time_ms == null ? "Unavailable" : `${agent.response_time_ms} ms`}
          </dd>
        </div>
      </dl>

      {agent.error_message ? <p className="mt-3 text-sm text-critical">{agent.error_message}</p> : null}
      {checking ? <p className="mt-3 text-xs text-ink-muted">Checking…</p> : null}

      {onCheckAgain ? (
        <Button variant="ghost" className="mt-3 px-0" onClick={onCheckAgain} disabled={checking}>
          <RefreshCw size={14} aria-hidden="true" />
          Check again
        </Button>
      ) : null}
    </Card>
  );
}
