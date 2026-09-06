import { useEffect, useMemo, useRef } from "react";
import { GeoJSON, MapContainer, Marker, TileLayer, Tooltip, ZoomControl, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import type { Feature, FeatureCollection } from "geojson";
import type { LatLngBoundsExpression, Layer, PathOptions } from "leaflet";
import L from "leaflet";

import { assetDivIcon, detectionDivIcon, incidentDivIcon } from "../../lib/leafletIcons";
import { assetMatchesLayer, MAP_TILE_ATTRIBUTION, MAP_TILE_URL, pipelineColor } from "../../lib/map";
import type {
  AssetFeature,
  DetectionCollection,
  DetectionFeature,
  IncidentFeature,
  MapLayerVisibility,
  MapSelection,
  PipelineFeature,
  ZoneFeature,
} from "../../types/map";
import type { AssetCollection, IncidentCollection, PipelineCollection, ZoneCollection } from "../../types/map";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

interface LiveMapCanvasProps {
  zones: ZoneCollection;
  pipelines: PipelineCollection;
  assets: AssetCollection;
  incidents: IncidentCollection;
  detections?: DetectionCollection;
  layers: MapLayerVisibility;
  selection: MapSelection;
  onSelect: (selection: MapSelection) => void;
  fitRequest: number;
  resetRequest: number;
  flyTo: [number, number] | null;
  onTilesFailed: () => void;
  interactive?: boolean;
  showControls?: boolean;
  maxFitZoom?: number;
  className?: string;
}

function boundsFromCollections(
  zones: ZoneCollection,
  pipelines: PipelineCollection,
  assets: AssetCollection,
  incidents: IncidentCollection,
  detections: DetectionCollection | undefined,
  layers: MapLayerVisibility,
): LatLngBoundsExpression | null {
  const collection: FeatureCollection = {
    type: "FeatureCollection",
    features: [
      ...(layers.zones ? zones.features : []),
      ...(layers.pipelines ? pipelines.features : []),
      ...assets.features.filter((feature) => assetMatchesLayer(feature.properties.asset_type, layers)),
      ...(layers.incidents ? incidents.features : []),
      ...(layers.detections && detections ? detections.features : []),
    ],
  };
  if (collection.features.length === 0) {
    return null;
  }
  const layer = L.geoJSON(collection);
  const bounds = layer.getBounds();
  return bounds.isValid() ? bounds : null;
}

function FitController({
  bounds,
  fitRequest,
  resetRequest,
  maxZoom,
}: {
  bounds: LatLngBoundsExpression | null;
  fitRequest: number;
  resetRequest: number;
  maxZoom: number;
}) {
  const map = useMap();
  const initial = useRef(false);
  const boundsRef = useRef(bounds);
  boundsRef.current = bounds;

  useEffect(() => {
    if (!bounds || initial.current) {
      return;
    }
    map.fitBounds(bounds, { padding: [36, 36], maxZoom, animate: false });
    initial.current = true;
  }, [bounds, map, maxZoom]);

  useEffect(() => {
    if (fitRequest === 0 && resetRequest === 0) {
      return;
    }
    const current = boundsRef.current;
    if (current) {
      map.fitBounds(current, { padding: [36, 36], maxZoom, animate: true });
    }
  }, [fitRequest, resetRequest, map, maxZoom]);

  return null;
}

function FlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) {
      map.flyTo(target, Math.max(map.getZoom(), 15), { duration: 0.6 });
    }
  }, [map, target]);
  return null;
}

function TileFailureWatcher({ onFail }: { onFail: () => void }) {
  const map = useMap();
  useEffect(() => {
    const handler = () => onFail();
    map.on("tileerror", handler);
    return () => {
      map.off("tileerror", handler);
    };
  }, [map, onFail]);
  return null;
}

export function LiveMapCanvas({
  zones,
  pipelines,
  assets,
  incidents,
  detections,
  layers,
  selection,
  onSelect,
  fitRequest,
  resetRequest,
  flyTo,
  onTilesFailed,
  interactive = true,
  showControls = true,
  maxFitZoom = 14,
  className = "h-full w-full",
}: LiveMapCanvasProps) {
  const bounds = useMemo(
    () => boundsFromCollections(zones, pipelines, assets, incidents, detections, layers),
    [zones, pipelines, assets, incidents, detections, layers],
  );

  const visibleAssets = assets.features.filter((feature) =>
    assetMatchesLayer(feature.properties.asset_type, layers),
  );
  const selectedId = selection?.feature.id ?? null;

  return (
    <MapContainer
      className={className}
      center={[24.5, 46.7]}
      zoom={5}
      scrollWheelZoom={interactive}
      dragging={interactive}
      zoomControl={false}
      attributionControl
      keyboard={interactive}
      aria-label="Demonstration water network map"
    >
      {showControls ? <ZoomControl position="bottomright" /> : null}
      <TileLayer url={MAP_TILE_URL} attribution={MAP_TILE_ATTRIBUTION} />
      <TileFailureWatcher onFail={onTilesFailed} />
      <FitController bounds={bounds} fitRequest={fitRequest} resetRequest={resetRequest} maxZoom={maxFitZoom} />
      <FlyTo target={flyTo} />

      {layers.zones
        ? zones.features.map((feature) => (
            <GeoJSON
              key={`zone-${feature.id}`}
              data={feature as Feature}
              style={(): PathOptions => ({
                color: "#08A6A6",
                weight: selection?.kind === "zone" && selectedId === feature.id ? 2 : 1,
                fillColor: "#08A6A6",
                fillOpacity: 0.08,
              })}
              eventHandlers={{
                click: () => onSelect({ kind: "zone", feature: feature as ZoneFeature }),
              }}
            />
          ))
        : null}

      {layers.pipelines
        ? pipelines.features.map((feature) => (
            <GeoJSON
              key={`pipe-${feature.id}`}
              data={feature as Feature}
              style={(): PathOptions => ({
                color: pipelineColor(feature.properties.status, feature.properties.criticality),
                weight: selection?.kind === "pipeline" && selectedId === feature.id ? 6 : 3,
                opacity: 0.95,
              })}
              eventHandlers={{
                click: () => onSelect({ kind: "pipeline", feature: feature as PipelineFeature }),
              }}
              onEachFeature={(_feat, layer: Layer) => {
                layer.bindTooltip(feature.properties.name, { sticky: true });
              }}
            />
          ))
        : null}

      <MarkerClusterGroup chunkedLoading showCoverageOnHover={false} maxClusterRadius={48}>
        {visibleAssets.map((feature) => {
          const [lon, lat] = feature.geometry.coordinates;
          return (
            <Marker
              key={`asset-${feature.id}`}
              position={[lat, lon]}
              icon={assetDivIcon(feature.properties.asset_type, feature.properties.operational_status)}
              eventHandlers={{
                click: () => onSelect({ kind: "asset", feature: feature as AssetFeature }),
              }}
            >
              <Tooltip>
                {feature.properties.name} · {feature.properties.external_id} · {feature.properties.operational_status}
              </Tooltip>
            </Marker>
          );
        })}
        {layers.incidents
          ? incidents.features.map((feature) => {
              const [lon, lat] = feature.geometry.coordinates;
              return (
                <Marker
                  key={`inc-${feature.id}`}
                  position={[lat, lon]}
                  icon={incidentDivIcon(feature.properties.severity, feature.properties.severity === "tier_3")}
                  zIndexOffset={400}
                  eventHandlers={{
                    click: () => onSelect({ kind: "incident", feature: feature as IncidentFeature }),
                  }}
                >
                  <Tooltip>
                    {feature.properties.incident_number} · {feature.properties.severity.replace("_", " ")} ·{" "}
                    {feature.properties.status.replaceAll("_", " ")}
                  </Tooltip>
                </Marker>
              );
            })
          : null}
        {layers.detections
          ? (detections?.features ?? []).map((feature) => {
              const [lon, lat] = feature.geometry.coordinates;
              return (
                <Marker
                  key={`det-${feature.id}`}
                  position={[lat, lon]}
                  icon={detectionDivIcon(feature.properties.priority)}
                  zIndexOffset={350}
                  eventHandlers={{
                    click: () => onSelect({ kind: "detection", feature: feature as DetectionFeature }),
                  }}
                >
                  <Tooltip>
                    {feature.properties.detection_number} · {feature.properties.priority} ·{" "}
                    {feature.properties.rule_code}
                  </Tooltip>
                </Marker>
              );
            })
          : null}
      </MarkerClusterGroup>
    </MapContainer>
  );
}
