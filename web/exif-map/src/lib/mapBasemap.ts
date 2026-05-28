import type { Map as MaplibreMap, StyleSpecification } from "maplibre-gl";

export const STREET_STYLE = "https://tiles.openfreemap.org/styles/liberty";

/** Switch to satellite + 3D buildings at this zoom and above */
export const ZOOM_SATELLITE = 14;

/** Double-click fly-to target zoom */
export const FLY_TO_ZOOM = 17;

export const DOUBLE_CLICK_MS = 400;

const BUILDINGS_LAYER_ID = "exif-3d-buildings";
const BUILDINGS_SOURCE_ID = "openfreemap-buildings";

export const SATELLITE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    satellite: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      maxzoom: 19,
      attribution: "Esri, Maxar, Earthstar Geographics",
    },
  },
  layers: [
    {
      id: "satellite",
      type: "raster",
      source: "satellite",
    },
  ],
};

function labelLayerId(map: MaplibreMap): string | undefined {
  const layers = map.getStyle()?.layers ?? [];
  for (const layer of layers) {
    if (
      layer.type === "symbol" &&
      layer.layout &&
      "text-field" in layer.layout &&
      layer.layout["text-field"]
    ) {
      return layer.id;
    }
  }
  return undefined;
}

export function setup3DBuildings(map: MaplibreMap): void {
  if (!map.isStyleLoaded()) return;
  if (map.getLayer(BUILDINGS_LAYER_ID)) return;

  if (!map.getSource(BUILDINGS_SOURCE_ID)) {
    map.addSource(BUILDINGS_SOURCE_ID, {
      type: "vector",
      url: "https://tiles.openfreemap.org/planet",
    });
  }

  map.addLayer(
    {
      id: BUILDINGS_LAYER_ID,
      source: BUILDINGS_SOURCE_ID,
      "source-layer": "building",
      type: "fill-extrusion",
      minzoom: ZOOM_SATELLITE,
      filter: ["!=", ["get", "hide_3d"], true],
      paint: {
        "fill-extrusion-color": "#c5cdd6",
        "fill-extrusion-height": [
          "interpolate",
          ["linear"],
          ["zoom"],
          ZOOM_SATELLITE,
          0,
          ZOOM_SATELLITE + 1.5,
          ["get", "render_height"],
        ],
        "fill-extrusion-base": [
          "case",
          [">=", ["zoom"], ZOOM_SATELLITE + 1],
          ["get", "render_min_height"],
          0,
        ],
        "fill-extrusion-opacity": 0.72,
      },
    },
    labelLayerId(map),
  );
}

export function remove3DBuildings(map: MaplibreMap): void {
  if (map.getLayer(BUILDINGS_LAYER_ID)) {
    map.removeLayer(BUILDINGS_LAYER_ID);
  }
  if (map.getSource(BUILDINGS_SOURCE_ID)) {
    map.removeSource(BUILDINGS_SOURCE_ID);
  }
}

export function useSatelliteBasemap(zoom: number): boolean {
  return zoom >= ZOOM_SATELLITE;
}
