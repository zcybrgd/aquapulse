import { useCallback, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { AssetType, OperationalStatus } from "../types/assets";
import type { IncidentStatus, SeverityTier } from "../types/incidents";
import type { MapFilters, MapLayerVisibility } from "../types/map";
import { DEFAULT_MAP_LAYERS, emptyMapFilters } from "../lib/map";

function asType(value: string | null): MapFilters["asset_type"] {
  const allowed: AssetType[] = ["sensor", "valve", "gateway"];
  return allowed.includes(value as AssetType) ? (value as AssetType) : "";
}

function asAssetStatus(value: string | null): MapFilters["asset_status"] {
  const allowed: OperationalStatus[] = ["online", "degraded", "offline"];
  return allowed.includes(value as OperationalStatus) ? (value as OperationalStatus) : "";
}

function asSeverity(value: string | null): MapFilters["incident_severity"] {
  const allowed: SeverityTier[] = ["tier_1", "tier_2", "tier_3"];
  return allowed.includes(value as SeverityTier) ? (value as SeverityTier) : "";
}

function asIncidentStatus(value: string | null): MapFilters["incident_status"] {
  const allowed: IncidentStatus[] = [
    "investigating",
    "awaiting_approval",
    "resolved",
  ];
  return allowed.includes(value as IncidentStatus) ? (value as IncidentStatus) : "";
}

function parseLayers(value: string | null): MapLayerVisibility {
  if (!value) {
    return { ...DEFAULT_MAP_LAYERS };
  }
  const tokens = new Set(value.split(",").filter(Boolean));
  return {
    zones: tokens.has("zones"),
    pipelines: tokens.has("pipelines"),
    sensors: tokens.has("sensors"),
    valves: tokens.has("valves"),
    gateways: tokens.has("gateways"),
    incidents: tokens.has("incidents"),
    detections: tokens.has("detections"),
  };
}

const MAP_SEARCH_STORAGE_KEY = "aquapulse.map.search";

function layersParam(layers: MapLayerVisibility): string | null {
  const defaults = DEFAULT_MAP_LAYERS;
  const same = (Object.keys(defaults) as Array<keyof MapLayerVisibility>).every(
    (key) => layers[key] === defaults[key],
  );
  if (same) {
    return null;
  }
  return (Object.keys(layers) as Array<keyof MapLayerVisibility>)
    .filter((key) => layers[key])
    .join(",");
}

export function useMapFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    if ([...searchParams.keys()].length > 0) {
      return;
    }
    const stored = sessionStorage.getItem(MAP_SEARCH_STORAGE_KEY);
    if (!stored) {
      return;
    }
    setSearchParams(new URLSearchParams(stored), { replace: true });
  }, [searchParams, setSearchParams]);

  const filters = useMemo<MapFilters>(
    () => ({
      zone: searchParams.get("zone") ?? "",
      asset_type: asType(searchParams.get("asset_type")),
      asset_status: asAssetStatus(searchParams.get("asset_status")),
      incident_severity: asSeverity(searchParams.get("incident_severity")),
      incident_status: asIncidentStatus(searchParams.get("incident_status")),
      include_resolved: searchParams.get("include_resolved") === "true",
    }),
    [searchParams],
  );

  const layers = useMemo(() => parseLayers(searchParams.get("layers")), [searchParams]);

  const hasActiveFilters = Boolean(
    filters.zone ||
      filters.asset_type ||
      filters.asset_status ||
      filters.incident_severity ||
      filters.incident_status ||
      filters.include_resolved,
  );

  const replace = useCallback(
    (nextFilters: MapFilters, nextLayers: MapLayerVisibility) => {
      const params = new URLSearchParams();
      if (nextFilters.zone) params.set("zone", nextFilters.zone);
      if (nextFilters.asset_type) params.set("asset_type", nextFilters.asset_type);
      if (nextFilters.asset_status) params.set("asset_status", nextFilters.asset_status);
      if (nextFilters.incident_severity) params.set("incident_severity", nextFilters.incident_severity);
      if (nextFilters.incident_status) params.set("incident_status", nextFilters.incident_status);
      if (nextFilters.include_resolved) params.set("include_resolved", "true");
      const layerValue = layersParam(nextLayers);
      if (layerValue) params.set("layers", layerValue);
      sessionStorage.setItem(MAP_SEARCH_STORAGE_KEY, params.toString());
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (patch: Partial<MapFilters>) => replace({ ...filters, ...patch }, layers),
    [filters, layers, replace],
  );

  const setLayers = useCallback(
    (patch: Partial<MapLayerVisibility>) => replace(filters, { ...layers, ...patch }),
    [filters, layers, replace],
  );

  const clearFilters = useCallback(() => replace(emptyMapFilters(), layers), [layers, replace]);

  return { filters, layers, setFilters, setLayers, clearFilters, hasActiveFilters };
}
