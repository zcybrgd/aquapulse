import { Link, useLocation, useNavigate } from "react-router-dom";

import { MAINTENANCE_LABELS, VALVE_POSITION_LABELS } from "../../lib/assets";
import { formatDateTime, formatNumber } from "../../lib/format";
import type { AssetSummary } from "../../types/assets";
import { Card } from "../ui/Card";
import { AssetHealthBar } from "./AssetHealthBar";
import { AssetStatusBadge } from "./AssetStatusBadge";
import { AssetTypeBadge } from "./AssetTypeBadge";

interface AssetListProps {
  items: AssetSummary[];
}

function detailsPath(id: string, search: string): string {
  return `/assets/${encodeURIComponent(id)}${search}`;
}

function typeSpecificValue(asset: AssetSummary): string {
  if (asset.asset_type === "valve") {
    return asset.current_position ? VALVE_POSITION_LABELS[asset.current_position] : "Position unknown";
  }
  if (asset.battery_pct !== null) {
    return `${formatNumber(asset.battery_pct, 0)}% battery`;
  }
  return "Powered";
}

export function AssetTable({ items }: AssetListProps) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Card className="hidden min-w-0 overflow-hidden xl:block">
      <table className="w-full table-fixed border-collapse text-left text-sm">
        <thead className="bg-page text-xs font-medium uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="w-[20%] px-4 py-3">Asset</th>
            <th className="w-[9%] px-4 py-3">Type</th>
            <th className="w-[11%] px-4 py-3">Status</th>
            <th className="w-[12%] px-4 py-3">Health</th>
            <th className="w-[12%] px-4 py-3">Zone</th>
            <th className="w-[12%] px-4 py-3">Pipeline</th>
            <th className="w-[10%] px-4 py-3">Signal / position</th>
            <th className="w-[8%] px-4 py-3">Last seen</th>
            <th className="w-[8%] px-4 py-3">Maintenance</th>
            <th className="w-[8%] px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((asset) => (
            <tr
              key={asset.external_id}
              className="cursor-pointer border-t border-line transition-colors hover:bg-teal-light/40"
              onClick={() => navigate(detailsPath(asset.external_id, location.search))}
            >
              <td className="px-4 py-3 align-top">
                <p className="font-medium text-ink">{asset.name}</p>
                <p className="mt-0.5 truncate text-xs text-ink-muted">{asset.external_id}</p>
                {asset.has_cellular_identity ? (
                  <p className="mt-1 truncate text-xs text-ink-muted">Cellular {asset.device_msisdn_masked}</p>
                ) : (
                  <p className="mt-1 text-xs text-ink-muted">No SIM</p>
                )}
              </td>
              <td className="px-4 py-3 align-top">
                <AssetTypeBadge type={asset.asset_type} />
              </td>
              <td className="px-4 py-3 align-top">
                <AssetStatusBadge status={asset.operational_status} />
              </td>
              <td className="px-4 py-3 align-top">
                <AssetHealthBar score={asset.health_score} />
              </td>
              <td className="px-4 py-3 align-top text-ink">
                <p>{asset.zone}</p>
                <p className="mt-0.5 truncate text-xs text-ink-muted" title={asset.location_label ?? undefined}>
                  {asset.location_label ?? "—"}
                </p>
              </td>
              <td className="px-4 py-3 align-top">
                <p className="truncate text-ink-muted">{asset.pipeline_segment ?? "—"}</p>
              </td>
              <td className="px-4 py-3 align-top text-ink">{typeSpecificValue(asset)}</td>
              <td className="px-4 py-3 align-top text-ink-muted">
                {asset.last_seen_at ? formatDateTime(asset.last_seen_at) : "—"}
              </td>
              <td className="px-4 py-3 align-top text-ink-muted">
                {MAINTENANCE_LABELS[asset.maintenance_state] ?? asset.maintenance_state}
              </td>
              <td className="px-4 py-3 align-top">
                <Link
                  to={detailsPath(asset.external_id, location.search)}
                  className="relative z-10 text-sm font-medium text-teal hover:underline"
                  onClick={(event) => event.stopPropagation()}
                >
                  View details
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export function AssetCardList({ items }: AssetListProps) {
  const location = useLocation();

  return (
    <ul className="space-y-3 xl:hidden">
      {items.map((asset) => (
        <li key={asset.external_id}>
          <Link
            to={detailsPath(asset.external_id, location.search)}
            className="card block min-w-0 p-4 hover:border-teal/30"
          >
            <div className="flex flex-wrap items-center gap-2">
              <AssetTypeBadge type={asset.asset_type} />
              <AssetStatusBadge status={asset.operational_status} />
            </div>
            <p className="mt-2 text-sm font-semibold text-ink">{asset.name}</p>
            <p className="mt-0.5 text-xs text-ink-muted">{asset.external_id}</p>
            <div className="mt-3">
              <AssetHealthBar score={asset.health_score} />
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-muted">
              <div>
                <dt>Zone</dt>
                <dd className="mt-0.5 text-ink">{asset.zone}</dd>
              </div>
              <div>
                <dt>Last seen</dt>
                <dd className="mt-0.5 text-ink">
                  {asset.last_seen_at ? formatDateTime(asset.last_seen_at) : "—"}
                </dd>
              </div>
              <div className="col-span-2">
                <dt>Location</dt>
                <dd className="mt-0.5 min-w-0 break-words text-ink">{asset.location_label ?? "—"}</dd>
              </div>
              <div className="col-span-2">
                <dt>Cellular</dt>
                <dd className="mt-0.5 text-ink">
                  {asset.has_cellular_identity ? asset.device_msisdn_masked : "Unavailable"}
                </dd>
              </div>
              <div className="col-span-2">
                <dt>Primary reading</dt>
                <dd className="mt-0.5 text-ink">{typeSpecificValue(asset)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-sm font-medium text-teal">View details</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
