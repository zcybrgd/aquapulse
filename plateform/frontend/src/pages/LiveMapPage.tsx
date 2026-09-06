import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Layers, Locate, Maximize2, RotateCcw, SlidersHorizontal } from "lucide-react";

import { LiveMapCanvas } from "../components/map/LiveMapCanvas";
import { MapFiltersBar } from "../components/map/MapFiltersBar";
import { MapInfoPanel } from "../components/map/MapInfoPanel";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Button } from "../components/ui/Button";
import { useMapData } from "../hooks/useMapData";
import { useMapFilters } from "../hooks/useMapFilters";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { fetchLatestTelemetryBatch } from "../api/telemetry";
import { fetchMapZones, fetchNearby } from "../api/map";
import { usePolling } from "../hooks/usePolling";
import type { LatestTelemetryBatch } from "../types/telemetry";
import { TelemetryStatusBar } from "../components/telemetry/TelemetryStatusBar";
import { formatDateTime } from "../lib/format";
import { assetMatchesLayer, emptyMapFilters } from "../lib/map";
import type { MapLayerVisibility, MapSelection, NearbyResponse, ZoneFeature } from "../types/map";

function zoneCenter(feature: ZoneFeature): [number, number] {
  const ring = feature.geometry.coordinates[0][0];
  const longitude = ring.reduce((sum, point) => sum + point[0], 0) / ring.length;
  const latitude = ring.reduce((sum, point) => sum + point[1], 0) / ring.length;
  return [latitude, longitude];
}

export default function LiveMapPage() {
  const location = useLocation();
  const compact = useMediaQuery("(max-width: 1023px)");
  const { filters, layers, setFilters, setLayers, clearFilters, hasActiveFilters } = useMapFilters();
  const { zones, pipelines, assets, incidents, detections, summary, loading, error, reload } = useMapData(
    filters,
    layers,
  );
  const [selection, setSelection] = useState<MapSelection>(null);
  const [legendOpen, setLegendOpen] = useState(!compact);
  const [panelOpen, setPanelOpen] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(!compact);
  const [fitRequest, setFitRequest] = useState(0);
  const [resetRequest, setResetRequest] = useState(0);
  const [flyTo, setFlyTo] = useState<[number, number] | null>(null);
  const [tilesFailed, setTilesFailed] = useState(false);
  const [locateLat, setLocateLat] = useState("25.0894");
  const [locateLon, setLocateLon] = useState("55.1392");
  const [nearby, setNearby] = useState<NearbyResponse | null>(null);
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null);
  const [telemetryRefreshing, setTelemetryRefreshing] = useState(false);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);
  const [telemetryBatch, setTelemetryBatch] = useState<LatestTelemetryBatch | null>(null);
  const [zoneNames, setZoneNames] = useState<string[]>([]);

  usePolling({
    enabled: true,
    intervalMs: 20_000,
    onTick: async (signal) => {
      try {
        const batch = await fetchLatestTelemetryBatch({ signal });
        setTelemetryBatch(batch);
        setTelemetryError(null);
        setLastRefreshAt(new Date().toISOString());
      } catch (caught) {
        const canceled =
          typeof caught === "object" &&
          caught !== null &&
          "code" in caught &&
          (caught as { code?: string }).code === "ERR_CANCELED";
        if (canceled) {
          return;
        }
        setTelemetryError("Telemetry refresh failed. Previous values are still shown.");
      }
    },
  });

  useEffect(() => {
    const controller = new AbortController();
    void fetchMapZones(emptyMapFilters(), { signal: controller.signal })
      .then((collection) => {
        setZoneNames(
          [...new Set(collection.features.map((feature) => feature.properties.name))].sort(),
        );
      })
      .catch(() => {
        /* Dropdown still works from the filtered layer if the unfiltered list fails. */
      });
    return () => controller.abort();
  }, []);

  const visibleAssets = assets.features.filter((feature) =>
    assetMatchesLayer(feature.properties.asset_type, layers),
  );
  const visibleCount =
    (layers.zones ? zones.features.length : 0) +
    (layers.pipelines ? pipelines.features.length : 0) +
    visibleAssets.length +
    (layers.incidents ? incidents.features.length : 0) +
    (layers.detections ? detections.features.length : 0);

  const criticalIncidents = incidents.features.filter((feature) => feature.properties.severity === "tier_3");
  const selectedTelemetry =
    selection?.kind === "asset"
      ? telemetryBatch?.items.find((item) => item.sensor_id === selection.feature.properties.external_id) ?? null
      : null;

  async function refreshTelemetry() {
    setTelemetryRefreshing(true);
    try {
      const batch = await fetchLatestTelemetryBatch();
      setTelemetryBatch(batch);
      setTelemetryError(null);
      setLastRefreshAt(new Date().toISOString());
    } catch {
      setTelemetryError("Telemetry refresh failed. Previous values are still shown.");
    } finally {
      setTelemetryRefreshing(false);
    }
  }

  async function locate() {
    const latitude = Number(locateLat);
    const longitude = Number(locateLon);
    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      return;
    }
    const result = await fetchNearby(latitude, longitude, 800);
    setNearby(result);
    setFlyTo([latitude, longitude]);
  }

  function toggleFullscreen() {
    const node = document.getElementById("live-map-shell");
    if (!node) {
      return;
    }
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void node.requestFullscreen();
    }
  }

  return (
    <div id="live-map-shell" className="flex h-full min-h-0 min-w-0 flex-col bg-page">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-line bg-white px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-ink">Live Network Map</h2>
            <span className="rounded-full bg-page px-2 py-0.5 text-[11px] font-medium text-ink-muted">
              Seeded demo
            </span>
          </div>
            <p className="mt-0.5 text-xs text-ink-muted">
              Persistent PostGIS geometries with batched simulated sensor freshness. Not live field telemetry.
            </p>
            <div className="mt-2">
              <TelemetryStatusBar
                lastUpdated={telemetryBatch?.last_telemetry_at ?? null}
                lastRefreshAt={lastRefreshAt}
                refreshing={telemetryRefreshing}
                backgroundError={telemetryError}
                onRefresh={() => void refreshTelemetry()}
              />
            </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {compact ? (
            <Button variant="secondary" className="h-9" onClick={() => setFiltersOpen(true)}>
              <SlidersHorizontal size={14} />
              Filters
            </Button>
          ) : null}
          <Button variant="secondary" className="h-9" onClick={() => setFitRequest((value) => value + 1)} aria-label="Fit map to visible features">
            Fit visible
          </Button>
          <Button variant="secondary" className="h-9" onClick={() => setResetRequest((value) => value + 1)} aria-label="Reset map view">
            <RotateCcw size={14} />
            Reset view
          </Button>
          <Button variant="secondary" className="h-9" onClick={toggleFullscreen} aria-label="Toggle full screen">
            <Maximize2 size={14} />
          </Button>
        </div>
      </header>

      {!compact ? (
        <div className="shrink-0 border-b border-line bg-white px-4 py-3">
          <MapFiltersBar
            filters={filters}
            zones={zoneNames}
            hasActiveFilters={hasActiveFilters}
            onChange={setFilters}
            onClear={clearFilters}
          />
        </div>
      ) : null}

      <div className="relative min-h-0 flex-1">
        {error ? (
          <div className="absolute inset-0 z-20 bg-white/90 p-6">
            <ErrorState message={error} onRetry={reload} />
          </div>
        ) : null}
        {loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70 text-sm text-ink-muted">
            Loading map layers…
          </div>
        ) : null}
        {!loading && !error && visibleCount === 0 ? (
          <div className="absolute inset-x-0 top-4 z-10 mx-auto w-[min(28rem,calc(100%-2rem))]">
            <div className="card p-4">
              <EmptyState
                title="No features match these filters"
                description="Clear filters or enable additional layers to see the demonstration network."
              />
            </div>
          </div>
        ) : null}

        <LiveMapCanvas
          className="absolute inset-0 h-full w-full"
          zones={zones}
          pipelines={pipelines}
          assets={assets}
          incidents={incidents}
          detections={detections}
          layers={layers}
          selection={selection}
          onSelect={(next) => {
            setSelection(next);
            setPanelOpen(true);
          }}
          fitRequest={fitRequest}
          resetRequest={resetRequest}
          flyTo={flyTo}
          onTilesFailed={() => setTilesFailed(true)}
        />

        {tilesFailed ? (
          <div className="absolute left-4 top-4 z-[1100] max-w-sm rounded-2xl border border-warning/40 bg-white p-3 text-sm text-ink shadow-card">
            Map tiles could not be loaded. Check the network or set VITE_MAP_TILE_URL. Feature geometry is still
            shown.
          </div>
        ) : null}

        <LayerLegend
          layers={layers}
          onChange={setLayers}
          open={legendOpen}
          onToggle={() => setLegendOpen((value) => !value)}
        />

        <aside
          className={`absolute z-[1100] overflow-y-auto bg-white shadow-card ${
            compact
              ? `inset-x-0 bottom-0 max-h-[48%] rounded-t-3xl border-t border-line ${panelOpen ? "" : "hidden"}`
              : `right-3 top-3 w-80 rounded-2xl border border-line ${panelOpen ? "" : "hidden"}`
          }`}
        >
          <MapInfoPanel
            selection={selection}
            search={location.search}
            telemetry={selectedTelemetry}
            onClose={() => {
              setSelection(null);
              if (compact) {
                setPanelOpen(false);
              }
            }}
            onZoomToZone={
              selection?.kind === "zone"
                ? () => setFlyTo(zoneCenter(selection.feature))
                : undefined
            }
          />
        </aside>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-3 border-t border-line bg-white px-4 py-2 text-xs text-ink-muted">
        <span>
          {layers.zones ? zones.features.length : 0} zones ·{" "}
          {layers.pipelines ? pipelines.features.length : 0} pipelines · {visibleAssets.length} assets ·{" "}
          {layers.incidents ? incidents.features.length : 0} incidents ·{" "}
          {layers.detections ? detections.features.length : 0} detections
        </span>
        <span>{summary ? `${summary.active_incidents} active incidents` : "—"}</span>
        <span>{summary ? `${summary.online} online · ${summary.degraded} degraded · ${summary.offline} offline` : ""}</span>
        <span className="ml-auto">
          {summary?.last_data_update ? `Updated ${formatDateTime(summary.last_data_update)}` : "Seeded demo"}
        </span>
      </div>

      <LocateBar
        latitude={locateLat}
        longitude={locateLon}
        onLatitude={setLocateLat}
        onLongitude={setLocateLon}
        onLocate={() => void locate()}
        nearbyCount={nearby?.total ?? null}
      />

      <ul className="sr-only">
        {criticalIncidents.map((incident) => (
          <li key={incident.id}>
            Critical incident {incident.properties.incident_number}: {incident.properties.title}
          </li>
        ))}
      </ul>

      {compact && filtersOpen ? (
        <div className="fixed inset-0 z-[700] bg-navy/40" role="dialog" aria-label="Map filters">
          <div className="absolute inset-x-0 bottom-0 max-h-[80%] overflow-y-auto rounded-t-3xl bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold text-ink">Filters</h3>
              <Button variant="ghost" onClick={() => setFiltersOpen(false)}>
                Done
              </Button>
            </div>
            <MapFiltersBar
              filters={filters}
              zones={zoneNames}
              compact
              hasActiveFilters={hasActiveFilters}
              onChange={setFilters}
              onClear={clearFilters}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function LayerLegend({
  layers,
  onChange,
  open,
  onToggle,
}: {
  layers: MapLayerVisibility;
  onChange: (patch: Partial<MapLayerVisibility>) => void;
  open: boolean;
  onToggle: () => void;
}) {
  const items: Array<[keyof MapLayerVisibility, string]> = [
    ["zones", "Zones"],
    ["pipelines", "Pipelines"],
    ["sensors", "Sensors"],
    ["valves", "Valves"],
    ["gateways", "Gateways"],
    ["incidents", "Incidents"],
    ["detections", "Detections"],
  ];
  return (
    <div className="absolute left-3 top-3 z-[1100] w-52">
      <Button
        variant="secondary"
        className="h-9 w-full justify-between"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls="map-layer-legend"
        aria-label="Toggle map layers"
      >
        <span className="inline-flex items-center gap-2">
          <Layers size={14} aria-hidden="true" />
          Layers
        </span>
      </Button>
      {open ? (
        <div id="map-layer-legend" className="mt-2 space-y-2 rounded-2xl border border-line bg-white p-3 text-sm shadow-card">
          {items.map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-ink">
              <input
                type="checkbox"
                checked={layers[key]}
                onChange={(event) => onChange({ [key]: event.target.checked })}
                aria-label={`Show ${label.toLowerCase()}`}
              />
              {label}
            </label>
          ))}
          <p className="pt-1 text-[11px] text-ink-muted">
            Circles sensors · diamonds valves · hexagons gateways · ! incidents · D detections
            (detections off by default)
          </p>
        </div>
      ) : null}
    </div>
  );
}

function LocateBar({
  latitude,
  longitude,
  onLatitude,
  onLongitude,
  onLocate,
  nearbyCount,
}: {
  latitude: string;
  longitude: string;
  onLatitude: (value: string) => void;
  onLongitude: (value: string) => void;
  onLocate: () => void;
  nearbyCount: number | null;
}) {
  return (
    <form
      className="flex shrink-0 flex-wrap items-center gap-2 border-t border-line bg-white px-4 py-2"
      onSubmit={(event) => {
        event.preventDefault();
        onLocate();
      }}
    >
      <Locate size={14} className="text-ink-muted" aria-hidden="true" />
      <label className="sr-only" htmlFor="map-lat">
        Latitude
      </label>
      <input
        id="map-lat"
        value={latitude}
        onChange={(event) => onLatitude(event.target.value)}
        className="h-9 w-28 rounded-xl border border-line px-2 text-sm"
        inputMode="decimal"
      />
      <label className="sr-only" htmlFor="map-lon">
        Longitude
      </label>
      <input
        id="map-lon"
        value={longitude}
        onChange={(event) => onLongitude(event.target.value)}
        className="h-9 w-28 rounded-xl border border-line px-2 text-sm"
        inputMode="decimal"
      />
      <Button type="submit" variant="secondary" className="h-9">
        Locate nearby
      </Button>
      {nearbyCount !== null ? <span className="text-xs text-ink-muted">{nearbyCount} features within 800 m</span> : null}
    </form>
  );
}
