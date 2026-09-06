import { CONTROL_MODE_LABELS, VALVE_POSITION_LABELS } from "../../lib/assets";
import { formatDateTime, formatDisplayDay, formatNumber } from "../../lib/format";
import type { AssetDetail } from "../../types/assets";
import { Card } from "../ui/Card";

interface AssetTypePanelProps {
  asset: AssetDetail;
}

function Row({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted" title={hint}>
        {label}
      </dt>
      <dd className="max-w-[60%] text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

export function AssetTypePanel({ asset }: AssetTypePanelProps) {
  if (asset.asset_type === "sensor" && asset.sensor) {
    return (
      <Card className="min-w-0 p-5">
        <h3 className="text-base font-semibold text-ink">Sensor characteristics</h3>
        <dl className="mt-4 space-y-3 text-sm">
          <Row label="Measurement types" value={asset.sensor.measurement_types.join(", ") || "—"} />
          <Row
            label="Sampling interval"
            value={
              asset.sensor.sampling_interval_seconds
                ? `${asset.sensor.sampling_interval_seconds} s`
                : "—"
            }
            hint="How often the device is configured to report a sample."
          />
          <Row
            label="Battery"
            value={asset.sensor.battery_pct !== null ? `${formatNumber(asset.sensor.battery_pct, 0)}%` : "—"}
          />
          <Row
            label="Signal strength"
            value={
              asset.sensor.signal_strength_dbm !== null
                ? `${asset.sensor.signal_strength_dbm} dBm`
                : "—"
            }
            hint="Received signal strength. Values closer to zero are stronger."
          />
          <Row
            label="Calibration"
            value={
              asset.sensor.calibration_date
                ? formatDisplayDay(asset.sensor.calibration_date)
                : "—"
            }
          />
          <Row label="Supported units" value={asset.sensor.supported_units.join(", ") || "—"} />
        </dl>
        {asset.sensor.measurement_ranges.length > 0 ? (
          <ul className="mt-4 space-y-2 text-sm">
            {asset.sensor.measurement_ranges.map((range) => (
              <li key={`${range.quantity}-${range.unit}`} className="rounded-2xl bg-page px-3 py-2">
                <p className="text-xs uppercase tracking-wide text-ink-muted">{range.quantity}</p>
                <p className="mt-0.5 font-medium text-ink">
                  {formatNumber(range.minimum, 1)}–{formatNumber(range.maximum, 1)} {range.unit}
                </p>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    );
  }

  if (asset.asset_type === "valve" && asset.valve) {
    return (
      <Card className="min-w-0 p-5">
        <h3 className="text-base font-semibold text-ink">Valve characteristics</h3>
        <dl className="mt-4 space-y-3 text-sm">
          <Row
            label="Current position"
            value={
              asset.valve.current_position
                ? VALVE_POSITION_LABELS[asset.valve.current_position]
                : "—"
            }
          />
          <Row
            label="Control mode"
            value={asset.valve.control_mode ? CONTROL_MODE_LABELS[asset.valve.control_mode] : "—"}
          />
          <Row label="Failsafe position" value={asset.valve.failsafe_position ?? "—"} />
          <Row label="Actuation type" value={asset.valve.actuation_type ?? "—"} />
          <Row
            label="Last known command"
            value={
              asset.valve.last_command_at ? formatDateTime(asset.valve.last_command_at) : "—"
            }
          />
        </dl>
      </Card>
    );
  }

  if (asset.asset_type === "gateway" && asset.gateway) {
    return (
      <Card className="min-w-0 p-5">
        <h3 className="text-base font-semibold text-ink">Gateway characteristics</h3>
        <dl className="mt-4 space-y-3 text-sm">
          <Row label="Provider" value={asset.gateway.provider ?? "—"} />
          <Row label="Connection type" value={asset.gateway.connection_type ?? "—"} />
          <Row label="Protocols" value={asset.gateway.protocols.join(", ") || "—"} />
          <Row
            label="Signal strength"
            value={
              asset.gateway.signal_strength_dbm !== null
                ? `${asset.gateway.signal_strength_dbm} dBm`
                : "—"
            }
            hint="Received signal strength. Values closer to zero are stronger."
          />
          <Row
            label="Packet delivery"
            value={asset.gateway.packet_delivery_status?.replace(/_/g, " ") ?? "—"}
          />
        </dl>
      </Card>
    );
  }

  return null;
}
