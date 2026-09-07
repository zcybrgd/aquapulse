import type {
  AssetSortField,
  AssetType,
  ControlMode,
  OperationalStatus,
  ValvePosition,
} from "../types/assets";

export const DEFAULT_ASSET_SORT_BY: AssetSortField = "health_score";
export const DEFAULT_ASSET_SORT_ORDER = "asc" as const;

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  sensor: "Sensor",
  valve: "Valve",
  gateway: "Gateway",
};

export const OPERATIONAL_STATUS_LABELS: Record<OperationalStatus, string> = {
  online: "Online",
  degraded: "Degraded",
  offline: "Offline",
};

export const VALVE_POSITION_LABELS: Record<ValvePosition, string> = {
  open: "Open",
  closed: "Closed",
  partial: "Partial",
  unknown: "Unknown",
};

export const CONTROL_MODE_LABELS: Record<ControlMode, string> = {
  manual: "Manual",
  remote: "Remote",
  automatic: "Automatic",
};

export const ASSET_SORT_LABELS: Record<AssetSortField, string> = {
  health_score: "Health score",
  name: "Name",
  asset_type: "Asset type",
  status: "Status",
  last_seen: "Last seen",
  next_maintenance: "Next maintenance",
};

export const MAINTENANCE_LABELS: Record<string, string> = {
  due: "Due now",
  upcoming: "Due within 30 days",
  scheduled: "Scheduled",
  not_scheduled: "Not scheduled",
};

export const READ_ONLY_HINT =
  "Asset Details shows maintenance records only. Create and update work from the Maintenance Center. Completing a record does not execute a device command.";

export function healthBand(score: number | null): "healthy" | "fair" | "poor" | "unknown" {
  if (score === null) {
    return "unknown";
  }
  if (score >= 80) {
    return "healthy";
  }
  if (score >= 60) {
    return "fair";
  }
  return "poor";
}

export function healthBandLabel(score: number | null): string {
  const band = healthBand(score);
  if (band === "healthy") {
    return "Healthy";
  }
  if (band === "fair") {
    return "Fair";
  }
  if (band === "poor") {
    return "Poor";
  }
  return "Unknown";
}

export function uniqueAssetZones(zones: string[]): string[] {
  return [...new Set(zones)].sort((left, right) => left.localeCompare(right));
}
