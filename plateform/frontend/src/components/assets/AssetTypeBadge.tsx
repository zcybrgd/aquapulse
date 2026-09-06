import { ASSET_TYPE_LABELS } from "../../lib/assets";
import type { AssetType } from "../../types/assets";
import { Badge } from "../ui/Badge";

const styles: Record<AssetType, string> = {
  sensor: "bg-teal-light text-teal",
  valve: "bg-[#eef6fb] text-navy",
  gateway: "bg-aqua-light text-navy",
};

interface AssetTypeBadgeProps {
  type: AssetType;
}

export function AssetTypeBadge({ type }: AssetTypeBadgeProps) {
  return <Badge className={styles[type]}>{ASSET_TYPE_LABELS[type]}</Badge>;
}
