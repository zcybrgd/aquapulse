import { formatNumber } from "../../lib/format";
import type { IncidentDetail } from "../../types/incidents";
import { Card } from "../ui/Card";

interface IncidentNetworkPanelProps {
  incident: IncidentDetail;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="text-right text-sm font-medium text-ink">{value}</p>
    </div>
  );
}

export function IncidentNetworkPanel({ incident }: IncidentNetworkPanelProps) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Network condition</h3>
      <p className="mt-0.5 text-sm text-ink-muted">{incident.network_condition}</p>
      <div className="mt-4 space-y-3">
        <Row label="Device reachability" value={incident.device_reachability} />
        <Row label="Signal strength" value={`${incident.signal_strength_dbm} dBm`} />
        <Row label="Packet loss" value={`${formatNumber(incident.packet_loss_percent, 1)}%`} />
        <Row label="Network priority" value={incident.network_priority_status} />
      </div>
    </Card>
  );
}
