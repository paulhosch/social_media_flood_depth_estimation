import { useCallback, useMemo, useRef, useState } from "react";
import { DeckGL } from "@deck.gl/react";
import { ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { FlyToInterpolator, WebMercatorViewport, type MapViewState } from "@deck.gl/core";
import Map, { type MapRef } from "react-map-gl/maplibre";
import type { Map as MaplibreMap } from "maplibre-gl";
import type { ColorMode, MapIndex, MapPoint } from "../lib/types";
import { applyColors } from "../lib/colors";
import {
  DOUBLE_CLICK_MS,
  FLY_TO_ZOOM,
  SATELLITE_STYLE,
  STREET_STYLE,
  setup3DBuildings,
  useSatelliteBasemap,
} from "../lib/mapBasemap";

interface ExifMapProps {
  index: MapIndex;
  colorMode: ColorMode;
  onSelect: (fileName: string) => void;
}

type ColoredPoint = MapPoint & {
  color: [number, number, number, number];
};

interface LocationCountLabel {
  lon: number;
  lat: number;
  count: number;
}

function locationKey(point: { lon: number; lat: number }): string {
  return `${point.lon.toFixed(5)},${point.lat.toFixed(5)}`;
}

function initialViewState(points: MapPoint[]) {
  if (points.length === 0) {
    return {
      longitude: 10.5,
      latitude: 51.2,
      zoom: 5,
      pitch: 0,
      bearing: 0,
    };
  }

  const lons = points.map((p) => p.lon);
  const lats = points.map((p) => p.lat);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);

  const viewport = new WebMercatorViewport({
    width: 800,
    height: 600,
  });
  const fitted = viewport.fitBounds(
    [
      [minLon, minLat],
      [maxLon, maxLat],
    ],
    { padding: 48, maxZoom: 14 },
  );

  return {
    longitude: fitted.longitude,
    latitude: fitted.latitude,
    zoom: fitted.zoom,
    pitch: 0,
    bearing: 0,
  };
}

export default function ExifMap({ index, colorMode, onSelect }: ExifMapProps) {
  const mapRef = useRef<MapRef>(null);
  const lastClickRef = useRef<{ fileName: string; time: number } | null>(null);
  const [viewState, setViewState] = useState<MapViewState>(() =>
    initialViewState(index.points),
  );

  const zoom = viewState.zoom ?? 0;
  const satelliteBasemap = useSatelliteBasemap(zoom);
  const mapStyle = satelliteBasemap ? SATELLITE_STYLE : STREET_STYLE;

  const sync3DBuildings = useCallback((map: MaplibreMap | undefined) => {
    if (!map) return;
    if (useSatelliteBasemap(map.getZoom())) {
      if (map.isStyleLoaded()) {
        setup3DBuildings(map);
      } else {
        map.once("idle", () => setup3DBuildings(map));
      }
    }
  }, []);

  const handleMapLoad = useCallback(() => {
    sync3DBuildings(mapRef.current?.getMap());
  }, [sync3DBuildings]);

  const handleStyleData = useCallback(() => {
    sync3DBuildings(mapRef.current?.getMap());
  }, [sync3DBuildings]);

  const flyToPoint = useCallback((point: ColoredPoint) => {
    setViewState((prev) => ({
      ...prev,
      longitude: point.lon,
      latitude: point.lat,
      zoom: FLY_TO_ZOOM,
      pitch: 55,
      bearing: prev.bearing ?? 0,
      transitionInterpolator: new FlyToInterpolator(),
      transitionDuration: 1200,
    }));
  }, []);

  const handlePointClick = useCallback(
    (point: ColoredPoint) => {
      const now = Date.now();
      const last = lastClickRef.current;

      if (
        last?.fileName === point.file_name &&
        now - last.time < DOUBLE_CLICK_MS
      ) {
        lastClickRef.current = null;
        flyToPoint(point);
        onSelect(point.file_name);
        return;
      }

      lastClickRef.current = { fileName: point.file_name, time: now };
      onSelect(point.file_name);
    },
    [flyToPoint, onSelect],
  );

  const coloredPoints = useMemo(
    () => applyColors(index.points, colorMode, index.time_range) as ColoredPoint[],
    [index.points, index.time_range, colorMode],
  );

  const locationCountLabels = useMemo(() => {
    const labels = new globalThis.Map<string, LocationCountLabel>();
    for (const point of coloredPoints) {
      const key = locationKey(point);
      if (labels.has(key)) continue;
      labels.set(key, {
        lon: point.lon,
        lat: point.lat,
        count: Math.max(1, point.stack_count),
      });
    }
    return Array.from(labels.values());
  }, [coloredPoints]);

  const layers = useMemo(
    () => [
      new ScatterplotLayer<ColoredPoint>({
        id: "exif-points",
        data: coloredPoints,
        getPosition: (d) => [d.lon, d.lat],
        getFillColor: (d) => d.color,
        getRadius: 7,
        radiusUnits: "pixels",
        pickable: true,
        autoHighlight: true,
        highlightColor: [255, 255, 255, 120],
        onClick: (info) => {
          if (info.object) handlePointClick(info.object);
        },
      }),
      new TextLayer<LocationCountLabel>({
        id: "exif-location-counts",
        data: locationCountLabels,
        getPosition: (d) => [d.lon, d.lat],
        getText: (d) => String(d.count),
        getSize: 12,
        sizeUnits: "pixels",
        getColor: [255, 255, 255, 255],
        getTextAnchor: "middle",
        getAlignmentBaseline: "center",
        getPixelOffset: [0, -15],
        background: true,
        getBackgroundColor: [15, 23, 42, 196],
        backgroundPadding: [5, 3],
        fontWeight: 700,
        pickable: false,
      }),
    ],
    [coloredPoints, handlePointClick, locationCountLabels],
  );

  const handleViewStateChange = useCallback(
    ({ viewState: next }: { viewState: MapViewState }) => {
      setViewState((prev) => {
        const nextZoom = (next as MapViewState).zoom ?? 0;
        const wasSatellite = useSatelliteBasemap(prev.zoom ?? 0);
        const isSatellite = useSatelliteBasemap(nextZoom);
        const state = next as MapViewState;

        if (isSatellite && !wasSatellite && (state.pitch ?? 0) < 25) {
          return { ...state, pitch: 45 };
        }
        if (!isSatellite && wasSatellite) {
          return { ...state, pitch: 0 };
        }
        return state;
      });
    },
    [],
  );

  return (
    <div className="exif-map">
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: next }) => handleViewStateChange({ viewState: next as MapViewState })}
        controller
        layers={layers}
        getCursor={({ isHovering }) => (isHovering ? "pointer" : "grab")}
      >
        <Map
          ref={mapRef}
          mapStyle={mapStyle}
          onLoad={handleMapLoad}
          onStyleData={handleStyleData}
        />
      </DeckGL>
      {satelliteBasemap && (
        <span className="exif-map__basemap-badge" aria-hidden>
          Satellite · 3D
        </span>
      )}
    </div>
  );
}
