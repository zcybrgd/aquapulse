import { formatDisplayDay, formatNumber } from "../../lib/format";
import type { AssetDetail } from "../../types/assets";
import { Card } from "../ui/Card";

interface AssetOverviewPanelProps {
  asset: AssetDetail;
}

function Row({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted" title={hint}>
        {label}
      </dt>
      <dd className="text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

export function AssetOverviewPanel({ asset }: AssetOverviewPanelProps) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Identity and location</h3>
      <dl className="mt-4 space-y-3 text-sm">
        <Row label="Manufacturer" value={asset.manufacturer ?? "—"} />
        <Row label="Model" value={asset.model ?? "—"} />
        <Row label="Serial number" value={asset.serial_number ?? "—"} />
        <Row
          label="Firmware"
          value={asset.firmware_version ?? "—"}
          hint="Installed software version on the field device."
        />
        <Row label="Zone" value={asset.zone} />
        <Row label="Pipeline segment" value={asset.pipeline_segment ?? "—"} />
        <Row
          label="Installed"
          value={asset.installed_at ? formatDisplayDay(asset.installed_at) : "—"}
        />
        <Row
          label="Commissioned"
          value={asset.commissioned_at ? formatDisplayDay(asset.commissioned_at) : "—"}
        />
        <Row
          label="Coordinates"
          value={
            asset.latitude !== null && asset.longitude !== null
              ? `${formatNumber(asset.latitude, 4)}, ${formatNumber(asset.longitude, 4)}`
              : "—"
          }
        />
      </dl>
    </Card>
  );
}
