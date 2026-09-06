import { isAxiosError } from "axios";
import { useEffect, useState } from "react";

import {
  fetchMapAssets,
  fetchMapDetections,
  fetchMapIncidents,
  fetchMapPipelines,
  fetchMapSummary,
  fetchMapZones,
} from "../api/map";
import type {
  AssetCollection,
  DetectionCollection,
  IncidentCollection,
  MapFilters,
  MapLayerVisibility,
  MapSummary,
  PipelineCollection,
  ZoneCollection,
} from "../types/map";
const EMPTY_ZONES: ZoneCollection = { type: "FeatureCollection", features: [] };
const EMPTY_PIPELINES: PipelineCollection = { type: "FeatureCollection", features: [] };
const EMPTY_ASSETS: AssetCollection = { type: "FeatureCollection", features: [] };
const EMPTY_INCIDENTS: IncidentCollection = { type: "FeatureCollection", features: [] };
const EMPTY_DETECTIONS: DetectionCollection = { type: "FeatureCollection", features: [] };

interface MapData {
  zones: ZoneCollection;
  pipelines: PipelineCollection;
  assets: AssetCollection;
  incidents: IncidentCollection;
  detections: DetectionCollection;
  summary: MapSummary | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useMapData(filters: MapFilters, layers: MapLayerVisibility): MapData {
  const [zones, setZones] = useState<ZoneCollection>(EMPTY_ZONES);
  const [pipelines, setPipelines] = useState<PipelineCollection>(EMPTY_PIPELINES);
  const [assets, setAssets] = useState<AssetCollection>(EMPTY_ASSETS);
  const [incidents, setIncidents] = useState<IncidentCollection>(EMPTY_INCIDENTS);
  const [detections, setDetections] = useState<DetectionCollection>(EMPTY_DETECTIONS);
  const [summary, setSummary] = useState<MapSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const handle = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      void Promise.all([
        fetchMapZones(filters, { signal: controller.signal }),
        fetchMapPipelines(filters, { signal: controller.signal }),
        fetchMapAssets(filters, { signal: controller.signal }),
        fetchMapIncidents(filters, { signal: controller.signal }),
        layers.detections
          ? fetchMapDetections(filters, { signal: controller.signal })
          : Promise.resolve(EMPTY_DETECTIONS),
        fetchMapSummary(filters, { signal: controller.signal }),
      ])
        .then(([zoneData, pipelineData, assetData, incidentData, detectionData, summaryData]) => {
          setZones(zoneData);
          setPipelines(pipelineData);
          setAssets(assetData);
          setIncidents(incidentData);
          setDetections(detectionData);
          setSummary(summaryData);
        })
        .catch((caught: unknown) => {
          if (isAxiosError(caught) && caught.code === "ERR_CANCELED") {
            return;
          }
          setError("We could not load map data from the AquaPulse service. Confirm the API is running, then try again.");
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
    }, 250);

    return () => {
      window.clearTimeout(handle);
      controller.abort();
    };
  }, [filters, layers.detections, reloadToken]);

  return {
    zones,
    pipelines,
    assets,
    incidents,
    detections,
    summary,
    loading,
    error,
    reload: () => setReloadToken((value) => value + 1),
  };
}
