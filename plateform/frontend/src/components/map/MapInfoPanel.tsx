import { Link } from "react-router-dom";

import { CLASSIFICATION_LABELS } from "../../lib/incidents";
import { formatDateTime, formatNumber, formatPercent } from "../../lib/format";
import { scorePercent } from "../../lib/detections";
import type { DetectionPriority, DetectionStatus } from "../../types/detections";
import type { MapSelection } from "../../types/map";
import type { LatestTelemetryResponse } from "../../types/telemetry";
import { FreshnessBadge, SimulatedTelemetryBadge } from "../telemetry/TelemetryBadges";
import { Button } from "../ui/Button";
import { AssetHealthBar } from "../assets/AssetHealthBar";
import { AssetStatusBadge } from "../assets/AssetStatusBadge";
import { AssetTypeBadge } from "../assets/AssetTypeBadge";
import { DetectionPriorityBadge } from "../detections/DetectionPriorityBadge";
import { DetectionStatusBadge } from "../detections/DetectionStatusBadge";
import { SeverityBadge } from "../incidents/SeverityBadge";
import { StatusBadge } from "../incidents/StatusBadge";

interface MapInfoPanelProps {
  selection: MapSelection;
  search: string;
  telemetry: LatestTelemetryResponse | null;
  onZoomToZone?: () => void;
  onClose: () => void;
}

export function MapInfoPanel({ selection, search, telemetry, onZoomToZone, onClose }: MapInfoPanelProps) {
  if (!selection) {
    return (
      <div className="p-4">
        <h3 className="text-sm font-semibold text-ink">Selection</h3>
        <p className="mt-2 text-sm text-ink-muted">
          Click a pipeline, asset, incident, detection or zone to inspect it. Demonstration geometries only.
        </p>
      </div>
    );
  }

  if (selection.kind === "asset") {
    const asset = selection.feature.properties;
    return (
      <div className="p-4">
        <Header title={asset.name} onClose={onClose} />
        <p className="text-sm font-medium text-teal">{asset.external_id}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <AssetTypeBadge type={asset.asset_type} />
          <AssetStatusBadge status={asset.operational_status} />
        </div>
        <div className="mt-3">
          <AssetHealthBar score={asset.health_score} />
        </div>
        <dl className="mt-3 space-y-2 text-sm">
          <Row label="Zone" value={asset.zone} />
          <Row label="Location" value={asset.location_label ?? "—"} />
          <Row
            label="Cellular"
            value={asset.has_cellular_identity ? asset.device_msisdn_masked ?? "Available" : "Unavailable"}
          />
          <Row label="Pipeline" value={asset.pipeline_segment ?? "—"} />
          <Row label="Last seen" value={asset.last_seen_at ? formatDateTime(asset.last_seen_at) : "—"} />
          <Row label="Active incidents" value={String(asset.active_incident_count)} />
        </dl>
        {asset.asset_type === "sensor" ? (
          <div className="mt-4 rounded-2xl bg-page p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <SimulatedTelemetryBadge />
              <FreshnessBadge
                state={telemetry?.freshness ?? asset.telemetry_freshness ?? "offline"}
              />
            </div>
            <dl className="space-y-2 text-sm">
              <Row
                label="Last reading"
                value={
                  (telemetry?.time ?? asset.latest_reading_at)
                    ? formatDateTime(telemetry?.time ?? asset.latest_reading_at ?? "")
                    : "—"
                }
              />
              <Row
                label="Packet loss"
                value={
                  (telemetry?.packet_loss_pct ?? asset.latest_packet_loss_pct) == null
                    ? "—"
                    : formatPercent(telemetry?.packet_loss_pct ?? asset.latest_packet_loss_pct ?? 0)
                }
              />
              <Row
                label="Signal"
                value={
                  (telemetry?.signal_strength_dbm ?? asset.latest_signal_strength_dbm) == null
                    ? "—"
                    : `${telemetry?.signal_strength_dbm ?? asset.latest_signal_strength_dbm} dBm`
                }
              />
              <Row
                label="Battery"
                value={
                  (telemetry?.battery_pct ?? asset.latest_battery_pct) == null
                    ? "—"
                    : formatPercent(telemetry?.battery_pct ?? asset.latest_battery_pct ?? 0)
                }
              />
            </dl>
          </div>
        ) : null}
        <Link
          to={`/assets/${encodeURIComponent(asset.external_id)}${search}`}
          className="mt-4 inline-flex text-sm font-medium text-teal hover:underline"
        >
          View asset details
        </Link>
      </div>
    );
  }

  if (selection.kind === "pipeline") {
    const pipe = selection.feature.properties;
    return (
      <div className="p-4">
        <Header title={pipe.name} onClose={onClose} />
        <p className="text-sm font-medium text-teal">{pipe.external_id}</p>
        <dl className="mt-3 space-y-2 text-sm">
          <Row label="Status" value={pipe.status} />
          <Row label="Criticality" value={`Tier ${pipe.criticality}`} />
          <Row label="Zone" value={pipe.zone} />
          <Row label="Population served" value={formatNumber(pipe.population_served)} />
          <Row label="Active incidents" value={String(pipe.active_incident_count)} />
          <Row label="Connected assets" value={String(pipe.connected_asset_count)} />
        </dl>
      </div>
    );
  }

  if (selection.kind === "incident") {
    const incident = selection.feature.properties;
    return (
      <div className="p-4">
        <Header title={incident.incident_number} onClose={onClose} />
        <p className="text-sm font-medium text-ink">{incident.title}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <SeverityBadge severity={incident.severity} />
          <StatusBadge status={incident.status} />
        </div>
        <p className="mt-3 text-sm text-ink-muted">{incident.summary}</p>
        <dl className="mt-3 space-y-2 text-sm">
          <Row label="Classification" value={CLASSIFICATION_LABELS[incident.classification]} />
          <Row label="Detected" value={formatDateTime(incident.detected_at)} />
          <Row label="Related asset" value={incident.related_asset_id ?? "—"} />
        </dl>
        <Link
          to={`/incidents/${encodeURIComponent(incident.incident_number)}${search}`}
          className="mt-4 inline-flex text-sm font-medium text-teal hover:underline"
        >
          View incident details
        </Link>
      </div>
    );
  }

  if (selection.kind === "detection") {
    const detection = selection.feature.properties;
    return (
      <div className="p-4">
        <Header title={detection.detection_number} onClose={onClose} />
        <p className="mt-1 text-sm text-ink">{detection.trigger_reason}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <DetectionPriorityBadge priority={detection.priority as DetectionPriority} />
          <DetectionStatusBadge status={detection.status as DetectionStatus} />
        </div>
        <dl className="mt-3 space-y-2 text-sm">
          <Row label="Rule" value={detection.rule_code} />
          <Row label="Sensor" value={detection.sensor_id} />
          <Row label="Zone" value={detection.zone} />
          <Row label="Score" value={scorePercent(detection.anomaly_score)} />
          <Row label="Detected" value={formatDateTime(detection.detected_at)} />
        </dl>
        <p className="mt-3 text-xs text-ink-muted">Not a confirmed incident.</p>
        <Link
          to={`/detections/${encodeURIComponent(detection.detection_number)}${search}`}
          className="mt-4 inline-flex text-sm font-medium text-teal hover:underline"
        >
          View detection details
        </Link>
      </div>
    );
  }

  const zone = selection.feature.properties;
  return (
    <div className="p-4">
      <Header title={zone.name} onClose={onClose} />
      <dl className="mt-3 space-y-2 text-sm">
        <Row label="Code" value={zone.code} />
        <Row label="Country" value={zone.country} />
        <Row label="Region" value={zone.region} />
        <Row label="Assets" value={String(zone.asset_count)} />
        <Row label="Active incidents" value={String(zone.active_incident_count)} />
      </dl>
      <Button className="mt-4 w-full" onClick={onZoomToZone}>
        Zoom to zone
      </Button>
    </div>
  );
}

function Header({ title, onClose }: { title: string; onClose: () => void }) {
  return (
    <div className="mb-2 flex items-start justify-between gap-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <button type="button" className="text-sm text-ink-muted hover:text-ink" onClick={onClose}>
        Close
      </button>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="shrink-0 text-ink-muted">{label}</dt>
      <dd className="min-w-0 break-words text-right font-medium text-ink">{value}</dd>
    </div>
  );
}
