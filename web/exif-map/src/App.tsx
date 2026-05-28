import { useCallback, useEffect, useMemo, useState } from "react";
import AppToolbar from "./components/AppToolbar";
import ExifMap from "./components/ExifMap";
import PanelResizer from "./components/PanelResizer";
import SidePanel from "./components/SidePanel";
import TimeHistogram from "./components/TimeHistogram";
import { buildFilteredMapIndex } from "./lib/floodClassification";
import {
  buildDepthFilteredMapIndex,
  mapHasFloodDepth,
} from "./lib/floodDepth";
import {
  filterMapIndexByTimeRange,
  type TimeRangeMs,
} from "./lib/timeRangeFilter";
import type {
  ColorMode,
  FloodClassificationFilter,
  FloodDepthFilter,
  MapIndex,
} from "./lib/types";
import { mapIndexUrl } from "./lib/config";

export default function App() {
  const [index, setIndex] = useState<MapIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [colorMode, setColorMode] = useState<ColorMode>("uniform");
  const [floodClassificationFilter, setFloodClassificationFilter] =
    useState<FloodClassificationFilter>("all");
  const [floodDepthFilter, setFloodDepthFilter] =
    useState<FloodDepthFilter>("all");
  const [timeRangeMs, setTimeRangeMs] = useState<TimeRangeMs | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(
    null,
  );
  const [panelWidth, setPanelWidth] = useState(380);

  const handlePanelResize = useCallback((width: number) => {
    setPanelWidth(Math.min(720, Math.max(280, width)));
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty(
      "--side-panel-width",
      `${panelWidth}px`,
    );
  }, [panelWidth]);

  useEffect(() => {
    fetch(mapIndexUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load map data (${res.status})`);
        return res.json() as Promise<MapIndex>;
      })
      .then(setIndex)
      .catch((err: Error) => setError(err.message));
  }, []);

  const hasFloodDepth = useMemo(
    () => (index ? mapHasFloodDepth(index) : false),
    [index],
  );

  const floodFilteredIndex = useMemo(() => {
    if (!index) return null;
    return buildFilteredMapIndex(index, floodClassificationFilter);
  }, [index, floodClassificationFilter]);

  const depthFilteredIndex = useMemo(() => {
    if (!floodFilteredIndex) return null;
    if (!hasFloodDepth) return floodFilteredIndex;
    return buildDepthFilteredMapIndex(floodFilteredIndex, floodDepthFilter);
  }, [floodFilteredIndex, floodDepthFilter, hasFloodDepth]);

  const displayIndex = useMemo(() => {
    if (!depthFilteredIndex) return null;
    if (!timeRangeMs) return depthFilteredIndex;
    return filterMapIndexByTimeRange(depthFilteredIndex, timeRangeMs);
  }, [depthFilteredIndex, timeRangeMs]);

  const handleFloodFilterChange = useCallback(
    (filter: FloodClassificationFilter) => {
      setFloodClassificationFilter(filter);
      setTimeRangeMs(null);
    },
    [],
  );

  const handleDepthFilterChange = useCallback((filter: FloodDepthFilter) => {
    setFloodDepthFilter(filter);
    setTimeRangeMs(null);
  }, []);

  const selectedPoint = useMemo(() => {
    if (!index || !selectedFileName) return null;
    return (
      index.points.find((p) => p.file_name === selectedFileName) ?? null
    );
  }, [index, selectedFileName]);

  const handleSelect = useCallback((fileName: string) => {
    setSelectedFileName(fileName);
  }, []);

  if (error) {
    return (
      <div className="app app--error">
        <p>{error}</p>
        <p>
          Run{" "}
          <code>.venv/bin/python scripts/enrich_flood_classification.py</code>,{" "}
          <code>.venv/bin/python scripts/enrich_flood_depth.py</code>, and{" "}
          <code>.venv/bin/python scripts/export_map_index.py</code> from the
          repo root after building the dataset.
        </p>
      </div>
    );
  }

  if (!index || !floodFilteredIndex || !depthFilteredIndex || !displayIndex) {
    return <div className="app app--loading">Loading map data…</div>;
  }

  return (
    <div className="app">
      <main className="app__main">
        <AppToolbar
          totalCount={index.point_count}
          filteredCount={displayIndex.point_count}
          timeRange={displayIndex.time_range}
          timeBrushRange={timeRangeMs}
          floodClassificationFilter={floodClassificationFilter}
          onFloodClassificationFilterChange={handleFloodFilterChange}
          floodDepthFilter={floodDepthFilter}
          onFloodDepthFilterChange={handleDepthFilterChange}
          hasFloodDepth={hasFloodDepth}
          colorMode={colorMode}
          onColorModeChange={setColorMode}
        />
        <TimeHistogram
          index={depthFilteredIndex}
          selectedTakenAt={selectedPoint?.taken_at ?? null}
          timeRangeMs={timeRangeMs}
          onTimeRangeChange={setTimeRangeMs}
        />
        <ExifMap
          index={displayIndex}
          colorMode={colorMode}
          onSelect={handleSelect}
        />
      </main>
      <PanelResizer panelWidth={panelWidth} onResize={handlePanelResize} />
      <SidePanel
        point={selectedPoint}
        hasFloodDepth={hasFloodDepth}
        width={panelWidth}
      />
    </div>
  );
}
