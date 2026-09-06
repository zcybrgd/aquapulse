import { lazy, Suspense } from "react";

import { Link } from "react-router-dom";

import { formatNumber } from "../../lib/format";
import type { AssetDetail } from "../../types/assets";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

const FocusedMap = lazy(() => import("../map/FocusedMap"));

interface AssetLocationPanelProps {
  asset: AssetDetail;
}

export function AssetLocationPanel({ asset }: AssetLocationPanelProps) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="text-base font-semibold text-ink">Location &amp; Connectivity</h3>
      <p className="mt-0.5 text-sm text-ink-muted">
        Direct zone, site label and masked device identity. The Asset Registry is read-only.
      </p>
      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Zone</dt>
          <dd className="text-right font-medium text-ink">
            {asset.zone_name}
            <span className="block text-xs font-normal text-ink-muted">{asset.zone_id}</span>
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Location</dt>
          <dd className="min-w-0 break-words text-right font-medium text-ink">{asset.location_label ?? "—"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Coordinates</dt>
          <dd className="text-right font-medium text-ink">
            {asset.latitude !== null && asset.longitude !== null
              ? `${formatNumber(asset.latitude, 4)}, ${formatNumber(asset.longitude, 4)}`
              : "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Cellular identity</dt>
          <dd className="text-right font-medium text-ink">
            {asset.has_cellular_identity ? "Available" : "Unavailable"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-muted">Device number</dt>
          <dd className="text-right font-medium text-ink">{asset.device_msisdn_masked ?? "—"}</dd>
        </div>
        {asset.signal_strength_dbm !== null ? (
          <div className="flex justify-between gap-3">
            <dt className="text-ink-muted">Signal</dt>
            <dd className="text-right font-medium text-ink">{asset.signal_strength_dbm} dBm</dd>
          </div>
        ) : null}
      </dl>
      <Link
        to={`/map?zone=${encodeURIComponent(asset.zone_name)}`}
        className="mt-3 inline-flex text-sm font-medium text-teal hover:underline"
      >
        Open zone on Live Map
      </Link>
      <p className="mt-4 text-xs text-ink-muted">
        Focused PostGIS view of this asset, its pipeline and nearby active incidents.
      </p>
      <div className="mt-4">
        <Suspense fallback={<Skeleton className="h-40 w-full rounded-2xl" />}>
          <FocusedMap variant="asset" asset={asset} />
        </Suspense>
      </div>
    </Card>
  );
}
