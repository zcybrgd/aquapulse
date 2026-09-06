import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { LiveMapCanvas } from "./LiveMapCanvas";
import { emptyMapFilters } from "../../lib/map";
import {
  fetchMapAssets,
  fetchMapIncidents,
  fetchMapPipelines,
} from "../../api/map";
import type { AssetDetail } from "../../types/assets";
import type { IncidentDetail } from "../../types/incidents";
import type {
  AssetCollection,
  IncidentCollection,
  MapSelection,
  PipelineCollection,
  ZoneCollection,
} from "../../types/map";

const EMPTY_ZONES: ZoneCollection = { type: "FeatureCollection", features: [] };
const EMPTY_PIPELINES: PipelineCollection = { type: "FeatureCollection", features: [] };
const EMPTY_ASSETS: AssetCollection = { type: "FeatureCollection", features: [] };
const EMPTY_INCIDENTS: IncidentCollection = { type: "FeatureCollection", features: [] };

interface FocusedMapProps {
  variant: "overview" | "incident" | "asset";
  incident?: IncidentDetail;
  asset?: AssetDetail;
}

export default function FocusedMap({ variant, incident, asset }: FocusedMapProps) {
  const [pipelines, setPipelines] = useState<PipelineCollection>(EMPTY_PIPELINES);
  const [assets, setAssets] = useState<AssetCollection>(EMPTY_ASSETS);
  const [incidents, setIncidents] = useState<IncidentCollection>(EMPTY_INCIDENTS);
  const [error, setError] = useState<string | null>(null);
  const [tilesFailed, setTilesFailed] = useState(false);
  const [selection, setSelection] = useState<MapSelection>(null);

  useEffect(() => {
    const controller = new AbortController();
    const filters = emptyMapFilters();
    void Promise.all([
      fetchMapPipelines(filters, { signal: controller.signal }),
      fetchMapAssets(filters, { signal: controller.signal }),
      fetchMapIncidents(filters, { signal: controller.signal }),
    ])
      .then(([pipeData, assetData, incidentData]) => {
        setPipelines(pipeData);
        setAssets(assetData);
        setIncidents(incidentData);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("Map preview is unavailable.");
        }
      });
    return () => controller.abort();
  }, []);

  const filtered = useMemo(() => {
    if (variant === "overview") {
      return { pipelines, assets, incidents };
    }
    if (variant === "incident" && incident) {
      return {
        pipelines: {
          type: "FeatureCollection" as const,
          features: pipelines.features.filter(
            (feature) =>
              feature.properties.external_id === incident.pipeline_segment ||
              feature.properties.name === incident.pipeline_segment,
          ),
        },
        assets: {
          type: "FeatureCollection" as const,
          features: assets.features.filter(
            (feature) =>
              feature.properties.external_id === incident.sensor ||
              feature.properties.external_id === incident.associated_valve,
          ),
        },
        incidents: {
          type: "FeatureCollection" as const,
          features: incidents.features.filter(
            (feature) => feature.properties.incident_number === incident.incident_number,
          ),
        },
      };
    }
    if (variant === "asset" && asset) {
      return {
        pipelines: {
          type: "FeatureCollection" as const,
          features: pipelines.features.filter(
            (feature) => feature.properties.name === asset.pipeline_segment,
          ),
        },
        assets: {
          type: "FeatureCollection" as const,
          features: assets.features.filter((feature) => feature.properties.external_id === asset.external_id),
        },
        incidents: {
          type: "FeatureCollection" as const,
          features: incidents.features.filter(
            (feature) =>
              feature.properties.related_asset_id === asset.external_id ||
              feature.properties.related_segment_id === asset.pipeline_segment,
          ),
        },
      };
    }
    return { pipelines: EMPTY_PIPELINES, assets: EMPTY_ASSETS, incidents: EMPTY_INCIDENTS };
  }, [variant, incident, asset, pipelines, assets, incidents]);

  return (
    <div className="relative min-h-0 overflow-hidden rounded-2xl border border-line">
      <div className="h-56 sm:h-64">
        {error ? (
          <p className="p-4 text-sm text-ink-muted">{error}</p>
        ) : (
          <LiveMapCanvas
            zones={EMPTY_ZONES}
            pipelines={filtered.pipelines}
            assets={filtered.assets}
            incidents={filtered.incidents}
            layers={{
              zones: false,
              pipelines: true,
              sensors: true,
              valves: true,
              gateways: true,
              incidents: true,
              detections: false,
            }}
            selection={selection}
            onSelect={setSelection}
            fitRequest={0}
            resetRequest={0}
            flyTo={null}
            onTilesFailed={() => setTilesFailed(true)}
            interactive={false}
            showControls={false}
            maxFitZoom={variant === "overview" ? 6 : 16}
          />
        )}
      </div>
      {tilesFailed ? (
        <p className="absolute left-3 top-3 rounded-xl bg-white/90 px-2 py-1 text-xs text-ink-muted">
          Tiles unavailable. Geometry still shown.
        </p>
      ) : null}
      {variant === "overview" ? (
        <div className="absolute bottom-3 right-3">
          <Link
            to="/map"
            className="rounded-xl bg-white/95 px-3 py-1.5 text-sm font-medium text-teal shadow-card hover:underline"
          >
            Open Live Map
          </Link>
        </div>
      ) : null}
    </div>
  );
}
