import L from "leaflet";

import type { AssetType, OperationalStatus } from "../types/assets";
import { incidentColor } from "./map";

import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

const defaultIconProto = L.Icon.Default.prototype as L.Icon.Default & {
  _getIconUrl?: string;
};
delete defaultIconProto._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
});

function markerHtml(
  shape: string,
  fill: string,
  label: string,
  extraClass = "",
): string {
  return `<span class="ap-marker ${shape} ${extraClass}" style="--marker:${fill}" title="${label}"><span class="ap-marker-label">${label}</span></span>`;
}

export function assetDivIcon(assetType: AssetType, status: OperationalStatus): L.DivIcon {
  const fill =
    status === "offline" ? "#E5484D" : status === "degraded" ? "#F59E0B" : "#08A6A6";
  const shape = assetType === "valve" ? "diamond" : assetType === "gateway" ? "hex" : "circle";
  const short = assetType === "valve" ? "V" : assetType === "gateway" ? "G" : "S";
  return L.divIcon({
    className: "ap-divicon",
    html: markerHtml(shape, fill, short, status),
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -12],
  });
}

export function incidentDivIcon(severity: string, pulse: boolean): L.DivIcon {
  const fill = incidentColor(severity);
  return L.divIcon({
    className: "ap-divicon",
    html: markerHtml("incident", fill, "!", pulse ? "incident-pulse" : ""),
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

export function detectionDivIcon(priority: string): L.DivIcon {
  const fill = priority === "critical" ? "#7C3AED" : priority === "high" ? "#6D28D9" : "#8B5CF6";
  return L.divIcon({
    className: "ap-divicon",
    html: markerHtml("detection", fill, "D"),
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -10],
  });
}
