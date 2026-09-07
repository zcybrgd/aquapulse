import type { LucideIcon } from "lucide-react";
import { Activity, Cable, Cpu, Headset, LayoutDashboard, Map, ScanSearch, ScrollText, Settings, TriangleAlert, Wifi, Wrench } from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  title: string;
  icon: LucideIcon;
}

export const primaryNav: NavItem[] = [
  { label: "Overview", path: "/", title: "Overview", icon: LayoutDashboard },
  { label: "Live Map", path: "/map", title: "Live Map", icon: Map },
  { label: "Incidents", path: "/incidents", title: "Incident Center", icon: TriangleAlert },
  { label: "Operations", path: "/operations", title: "Operations Center", icon: Headset },
  { label: "Investigation Queue", path: "/detections", title: "Investigation Queue", icon: ScanSearch },
  { label: "Assets", path: "/assets", title: "Asset Registry", icon: Cpu },
  { label: "Maintenance", path: "/maintenance", title: "Maintenance Center", icon: Wrench },
  { label: "Integrations", path: "/integrations", title: "Integration Readiness", icon: Cable },
  { label: "Network Health", path: "/network", title: "Network Health", icon: Wifi },
  { label: "Analytics", path: "/analytics", title: "Analytics", icon: Activity },
  { label: "Agent Audit", path: "/agent-audit", title: "Agent Audit Trail", icon: ScrollText },
];

export const utilityNav: NavItem[] = [
  { label: "Settings", path: "/settings", title: "Settings", icon: Settings },
];

export const allNavItems = [...primaryNav, ...utilityNav];

export function getPageTitle(pathname: string): string {
  if (/^\/incidents\/.+/.test(pathname)) {
    return "Incident details";
  }
  if (/^\/detections\/.+/.test(pathname)) {
    return "Detection details";
  }
  if (/^\/assets\/.+/.test(pathname)) {
    return "Asset details";
  }
  if (/^\/maintenance\/work-orders\/.+/.test(pathname)) {
    return "Work order details";
  }
  if (/^\/integrations\/runs\/.+/.test(pathname)) {
    return "Agent run";
  }
  if (/^\/integrations\/findings\/.+/.test(pathname)) {
    return "Agent finding";
  }
  if (/^\/integrations\/recommendations\/.+/.test(pathname)) {
    return "Agent recommendation";
  }
  if (/^\/agent-audit\/runs\/.+/.test(pathname)) {
    return "Agent audit run";
  }
  if (pathname === "/network-health") {
    return "Network Health";
  }
  const match = allNavItems.find((item) => item.path === pathname);
  return match?.title ?? "AquaPulse";
}
