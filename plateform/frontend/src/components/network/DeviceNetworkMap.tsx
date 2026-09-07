import { Circle, CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

import { MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from "../../lib/map";

import "leaflet/dist/leaflet.css";

interface DeviceNetworkMapProps {
  registeredLatitude: number | null;
  registeredLongitude: number | null;
  networkLatitude: number | null;
  networkLongitude: number | null;
  accuracyRadiusM: number | null;
}

export function DeviceNetworkMap({
  registeredLatitude,
  registeredLongitude,
  networkLatitude,
  networkLongitude,
  accuracyRadiusM,
}: DeviceNetworkMapProps) {
  const points = [
    registeredLatitude != null && registeredLongitude != null
      ? ([registeredLatitude, registeredLongitude] as [number, number])
      : null,
    networkLatitude != null && networkLongitude != null
      ? ([networkLatitude, networkLongitude] as [number, number])
      : null,
  ].filter((point): point is [number, number] => point !== null);

  if (points.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center rounded-xl bg-page text-sm text-ink-muted">
        No coordinates available for this device.
      </div>
    );
  }

  const center = points[0];

  return (
    <div className="h-56 min-w-0 overflow-hidden rounded-xl border border-line">
      <MapContainer
        center={center}
        zoom={15}
        className="h-full w-full"
        scrollWheelZoom={false}
        zoomControl
      >
        <TileLayer url={MAP_TILE_URL} attribution={MAP_TILE_ATTRIBUTION} />
        {registeredLatitude != null && registeredLongitude != null ? (
          <CircleMarker
            center={[registeredLatitude, registeredLongitude]}
            radius={8}
            pathOptions={{ color: "#0f766e", fillColor: "#0f766e", fillOpacity: 0.9 }}
          >
            <Tooltip permanent>Registered location</Tooltip>
          </CircleMarker>
        ) : null}
        {networkLatitude != null && networkLongitude != null ? (
          <>
            {accuracyRadiusM != null && accuracyRadiusM > 0 ? (
              <Circle
                center={[networkLatitude, networkLongitude]}
                radius={accuracyRadiusM}
                pathOptions={{ color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.12 }}
              />
            ) : null}
            <CircleMarker
              center={[networkLatitude, networkLongitude]}
              radius={7}
              pathOptions={{ color: "#b45309", fillColor: "#f59e0b", fillOpacity: 0.9 }}
            >
              <Tooltip permanent>Network-derived location</Tooltip>
            </CircleMarker>
          </>
        ) : null}
      </MapContainer>
    </div>
  );
}
