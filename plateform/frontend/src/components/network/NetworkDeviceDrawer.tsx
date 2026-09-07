import { Link } from "react-router-dom";
import { X } from "lucide-react";

import { formatDateTime, formatNumber } from "../../lib/format";
import type { DeviceNetworkDetail } from "../../types/networkHealth";
import { Button } from "../ui/Button";
import { DeviceNetworkMap } from "./DeviceNetworkMap";
import { ReachabilityBadge, SourceModeBadge, reachabilityLabel } from "./ReachabilityBadge";

interface NetworkDeviceDrawerProps {
  device: DeviceNetworkDetail;
  refreshing: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="max-w-[16rem] text-right text-sm font-medium text-ink">{value}</p>
    </div>
  );
}

export function NetworkDeviceDrawer({
  device,
  refreshing,
  onClose,
  onRefresh,
}: NetworkDeviceDrawerProps) {
  return (
    <aside className="fixed inset-x-0 bottom-0 z-30 max-h-[88vh] overflow-y-auto border-t border-line bg-white p-5 shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:h-full md:w-[28rem] md:max-h-none md:border-l md:border-t-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Device</p>
          <h3 className="truncate text-lg font-semibold text-ink">{device.asset_id}</h3>
          <p className="text-sm text-ink-muted">{device.asset_name}</p>
        </div>
        <Button variant="ghost" onClick={onClose} aria-label="Close device details">
          <X size={16} />
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <ReachabilityBadge status={device.reachability_status} />
        <SourceModeBadge mode={device.source_mode} label={device.data_source_label} />
      </div>

      <div className="mt-5 space-y-3">
        <Row label="Type" value={device.asset_type} />
        <Row label="Zone" value={device.zone_name ?? "—"} />
        <Row label="Location label" value={device.location_label ?? "—"} />
        <Row
          label="Cellular identity"
          value={device.has_cellular_identity ? (device.device_msisdn_masked ?? "Masked identity") : "No SIM"}
        />
        <Row label="Reachability" value={reachabilityLabel(device.reachability_status)} />
        <Row label="Reachable via" value={device.reachable_via ?? "—"} />
        <Row
          label="Registered location"
          value={
            device.registered_latitude != null && device.registered_longitude != null
              ? `${device.registered_latitude.toFixed(5)}, ${device.registered_longitude.toFixed(5)}`
              : "—"
          }
        />
        <Row
          label="Network-derived location"
          value={
            device.network_location_available &&
            device.network_latitude != null &&
            device.network_longitude != null
              ? `${device.network_latitude.toFixed(5)}, ${device.network_longitude.toFixed(5)}`
              : "Unavailable"
          }
        />
        <Row
          label="Accuracy radius"
          value={
            device.accuracy_radius_m != null
              ? `${formatNumber(device.accuracy_radius_m, 0)} m · cell observation, not GPS`
              : "—"
          }
        />
        <Row
          label="Offset from registered"
          value={device.location_offset_m != null ? `${formatNumber(device.location_offset_m, 0)} m` : "—"}
        />
        <Row
          label="Last telemetry"
          value={
            device.last_telemetry?.observed_at
              ? formatDateTime(device.last_telemetry.observed_at)
              : "No sensor reading"
          }
        />
        <Row label="Last check" value={device.retrieved_at ? formatDateTime(device.retrieved_at) : "—"} />
        <Row label="Provider" value={device.provider ?? "—"} />
      </div>

      {device.error_message ? (
        <p className="mt-4 rounded-xl bg-warning/15 p-3 text-sm text-ink">{device.error_message}</p>
      ) : null}

      <div className="mt-5">
        <DeviceNetworkMap
          registeredLatitude={device.registered_latitude}
          registeredLongitude={device.registered_longitude}
          networkLatitude={device.network_latitude}
          networkLongitude={device.network_longitude}
          accuracyRadiusM={device.accuracy_radius_m}
        />
        <p className="mt-2 text-xs text-ink-muted">
          Teal is the registered PostGIS installation point. Amber is the Nokia network-derived
          observation and its accuracy circle.
        </p>
      </div>

      {device.history.length > 0 ? (
        <div className="mt-5">
          <h4 className="text-sm font-semibold text-ink">Snapshot history</h4>
          <ul className="mt-2 space-y-2">
            {device.history.slice(0, 8).map((item) => (
              <li key={item.snapshot_id} className="rounded-xl bg-page px-3 py-2 text-sm">
                <p className="font-medium text-ink">{item.snapshot_id}</p>
                <p className="text-ink-muted">
                  {reachabilityLabel(item.reachability_status)} · {formatDateTime(item.retrieved_at)}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-3">
        <Button onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh network"}
        </Button>
        <Link to={`/assets/${encodeURIComponent(device.asset_id)}`} className="text-sm font-medium text-teal hover:underline">
          Asset details
        </Link>
        <Link
          to={`/map?asset=${encodeURIComponent(device.asset_id)}`}
          className="text-sm font-medium text-teal hover:underline"
        >
          Live Map
        </Link>
      </div>
    </aside>
  );
}
