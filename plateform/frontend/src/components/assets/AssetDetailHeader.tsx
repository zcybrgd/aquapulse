import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { formatDateTime } from "../../lib/format";
import type { AssetDetail } from "../../types/assets";
import { AssetHealthBar } from "./AssetHealthBar";
import { AssetStatusBadge } from "./AssetStatusBadge";
import { AssetTypeBadge } from "./AssetTypeBadge";

interface AssetDetailHeaderProps {
  asset: AssetDetail;
}

export function AssetDetailHeader({ asset }: AssetDetailHeaderProps) {
  const location = useLocation();

  return (
    <div className="min-w-0">
      <Link
        to={`/assets${location.search}`}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-teal hover:underline"
      >
        <ArrowLeft size={16} aria-hidden="true" />
        Back to Asset Registry
      </Link>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-teal">{asset.external_id}</p>
        <AssetTypeBadge type={asset.asset_type} />
        <AssetStatusBadge status={asset.operational_status} />
      </div>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">{asset.name}</h2>
      <div className="mt-4 grid max-w-xl grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs text-ink-muted">Health score</p>
          <div className="mt-1">
            <AssetHealthBar score={asset.health_score} />
          </div>
        </div>
        <div>
          <p className="text-xs text-ink-muted">Last seen</p>
          <p className="mt-1 text-sm font-medium text-ink">
            {asset.last_seen_at ? formatDateTime(asset.last_seen_at) : "Not reporting"}
          </p>
        </div>
      </div>
    </div>
  );
}
