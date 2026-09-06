import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

import { fetchNetworkSummary } from "../../api/networkHealth";
import type { DashboardSummary, TelemetryReading } from "../../types/api";
import type { NetworkFilters, NetworkSummary } from "../../types/networkHealth";
import { formatDateTime, formatNumber, formatPercent } from "../../lib/format";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

interface NetworkHealthPanelProps {
  summary: DashboardSummary;
  telemetry: TelemetryReading[];
}

const EMPTY_FILTERS: NetworkFilters = {
  event_type: "",
  status: "",
  device: "",
  cluster: "",
  incident: "",
  search: "",
  start: "",
  end: "",
};

function displayCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return formatNumber(value, 0);
}

export function NetworkHealthPanel({ summary, telemetry }: NetworkHealthPanelProps) {
  const reduceMotion = useReducedMotion();
  const [network, setNetwork] = useState<NetworkSummary | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);
  const sensorRatio =
    summary.total_sensors === 0 ? 0 : (summary.online_sensors / summary.total_sensors) * 100;
  const averagePacketLoss =
    telemetry.length === 0
      ? null
      : telemetry.reduce((total, reading) => total + reading.packet_loss, 0) / telemetry.length;
  const packetDelivery =
    averagePacketLoss === null ? null : Math.max(0, 100 - averagePacketLoss);

  useEffect(() => {
    const controller = new AbortController();
    void fetchNetworkSummary(EMPTY_FILTERS, { signal: controller.signal })
      .then((data) => {
        setNetwork(data);
        setNetworkError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setNetwork(null);
          setNetworkError("Mock Network Agent logs are unavailable.");
        }
      });
    return () => controller.abort();
  }, []);

  const logRows = [
    { label: "Connectivity checks", value: network ? displayCount(network.connectivity_checks) : "—" },
    { label: "QoD grants", value: network ? displayCount(network.grants) : "—" },
    { label: "QoD denials", value: network ? displayCount(network.denials) : "—" },
    { label: "QoD releases", value: network ? displayCount(network.releases) : "—" },
    { label: "Network Agent errors", value: network ? displayCount(network.errors) : "—" },
    {
      label: "Latest event",
      value: network?.latest_event_at ? formatDateTime(network.latest_event_at) : "—",
    },
  ];

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: 0.2, ease: "easeOut" }}
    >
      <Card className="min-w-0 p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold text-ink">Network Agent logs</h3>
            <p className="mt-0.5 text-sm text-ink-muted">
              Mock Network Agent logs — final contract pending
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className="bg-warning/15 text-ink">Mock agent data</Badge>
            <Badge className="bg-page text-ink">Awaiting confirmation</Badge>
          </div>
        </div>
        <p className="mt-3 text-sm font-medium text-ink">
          Network Agent contract awaiting team confirmation
        </p>
        {networkError ? <p className="mt-2 text-sm text-critical">{networkError}</p> : null}
        <ul className="mt-4 space-y-3">
          {logRows.map((row) => (
            <li key={row.label} className="flex items-start justify-between gap-4">
              <p className="text-sm text-ink-muted">{row.label}</p>
              <p className="text-sm font-medium text-ink">{row.value}</p>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-ink-muted">
          Simulated telemetry only: {formatPercent(sensorRatio)} sensors reporting
          {packetDelivery === null ? "" : ` · packet delivery ${formatPercent(packetDelivery)}`}.
          These are TimescaleDB counts, not Network Agent decisions.
        </p>
        <Link to="/network" className="mt-4 inline-block text-sm font-medium text-teal hover:underline">
          Open Network Health
        </Link>
      </Card>
    </motion.div>
  );
}
