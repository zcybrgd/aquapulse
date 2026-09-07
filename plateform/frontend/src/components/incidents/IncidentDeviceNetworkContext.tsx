import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchIncidentDeviceNetwork, refreshIncidentDeviceNetwork } from "../../api/networkHealth";
import { formatDateTime, formatNumber } from "../../lib/format";
import type { IncidentDeviceNetworkContext as Context } from "../../types/networkHealth";
import { ReachabilityBadge, SourceModeBadge } from "../network/ReachabilityBadge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

interface IncidentDeviceNetworkContextProps {
  incidentId: string;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="text-right text-sm font-medium text-ink">{value}</p>
    </div>
  );
}

export function IncidentDeviceNetworkContext({ incidentId }: IncidentDeviceNetworkContextProps) {
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void fetchIncidentDeviceNetwork(incidentId, { signal: controller.signal })
      .then((next) => {
        setContext(next);
        setError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("Device network context is unavailable.");
        }
      });
    return () => controller.abort();
  }, [incidentId]);

  async function refresh() {
    setRefreshing(true);
    try {
      setContext(await refreshIncidentDeviceNetwork(incidentId, false));
      setError(null);
    } catch {
      setError("Network context refresh did not complete.");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Device Network Context</h3>
      <p className="mt-0.5 text-sm text-ink-muted">
        Nokia reachability is not incident status. Investigating, waiting for approval, and resolved
        remain incident workflow states.
      </p>
      {error ? <p className="mt-3 text-sm text-critical">{error}</p> : null}
      {context && context.source_mode !== "nokia_live" && context.source_mode !== "nokia_simulator" ? (
        <p className="mt-4 text-sm text-ink-muted">Network data source not connected</p>
      ) : !context?.available ? (
        <p className="mt-4 text-sm text-ink-muted">No affected device is linked to this incident.</p>
      ) : (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {context.reachability_status ? <ReachabilityBadge status={context.reachability_status} /> : null}
            <SourceModeBadge mode={context.source_mode} label={context.data_source_label ?? undefined} />
          </div>
          <Row
            label="Last reachability check"
            value={context.reachability_checked_at ? formatDateTime(context.reachability_checked_at) : "—"}
          />
          <Row
            label="Nokia-derived location"
            value={
              context.network_location_available &&
              context.network_latitude != null &&
              context.network_longitude != null
                ? `${context.network_latitude.toFixed(5)}, ${context.network_longitude.toFixed(5)}`
                : "Unavailable"
            }
          />
          <Row
            label="Accuracy radius"
            value={context.accuracy_radius_m != null ? `${formatNumber(context.accuracy_radius_m, 0)} m` : "—"}
          />
          <Row
            label="Registered asset location"
            value={
              context.registered_latitude != null && context.registered_longitude != null
                ? `${context.registered_latitude.toFixed(5)}, ${context.registered_longitude.toFixed(5)}`
                : "—"
            }
          />
          <Row label="Data source" value={context.data_source_label ?? "—"} />
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button variant="secondary" onClick={() => void refresh()} disabled={refreshing || !context?.available}>
          {refreshing ? "Refreshing…" : "Refresh network context"}
        </Button>
        {context?.asset_id ? (
          <Link
            to={`/network-health?device=${encodeURIComponent(context.asset_id)}`}
            className="text-sm font-medium text-teal hover:underline"
          >
            Network Health details
          </Link>
        ) : null}
      </div>
    </Card>
  );
}
