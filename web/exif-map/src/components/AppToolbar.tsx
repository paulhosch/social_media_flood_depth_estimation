import { FLOOD_CLASSIFICATION_FILTER_LABELS } from "../lib/floodClassification";
import { FLOOD_DEPTH_FILTER_LABELS } from "../lib/floodDepth";
import { COLOR_MODE_LABELS } from "../lib/colors";
import { formatToolbarSummary } from "../lib/timelineSummary";
import type { TimeRangeMs } from "../lib/timeRangeFilter";
import type {
  ColorMode,
  FloodClassificationFilter,
  FloodDepthFilter,
} from "../lib/types";

interface AppToolbarProps {
  totalCount: number;
  filteredCount: number;
  timeRange: { min: string | null; max: string | null };
  timeBrushRange: TimeRangeMs | null;
  floodClassificationFilter: FloodClassificationFilter;
  onFloodClassificationFilterChange: (
    filter: FloodClassificationFilter,
  ) => void;
  floodDepthFilter: FloodDepthFilter;
  onFloodDepthFilterChange: (filter: FloodDepthFilter) => void;
  hasFloodDepth: boolean;
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
}

export default function AppToolbar({
  totalCount,
  filteredCount,
  timeRange,
  timeBrushRange,
  floodClassificationFilter,
  onFloodClassificationFilterChange,
  floodDepthFilter,
  onFloodDepthFilterChange,
  hasFloodDepth,
  colorMode,
  onColorModeChange,
}: AppToolbarProps) {
  const summary = formatToolbarSummary({
    totalCount,
    filteredCount,
    timeRange,
    timeBrushRange,
  });

  const colorModes = (Object.keys(COLOR_MODE_LABELS) as ColorMode[]).filter(
    (mode) => hasFloodDepth || mode !== "flood_depth",
  );

  return (
    <header className="app-toolbar">
      <h1 className="app-toolbar__title">EXIF image map</h1>
      <p className="app-toolbar__summary">{summary}</p>
      <div className="app-toolbar__controls">
        <label className="app-toolbar__control">
          <span>Flood classification</span>
          <select
            value={floodClassificationFilter}
            onChange={(e) =>
              onFloodClassificationFilterChange(
                e.target.value as FloodClassificationFilter,
              )
            }
          >
            {(
              Object.keys(
                FLOOD_CLASSIFICATION_FILTER_LABELS,
              ) as FloodClassificationFilter[]
            ).map((filter) => (
              <option key={filter} value={filter}>
                {FLOOD_CLASSIFICATION_FILTER_LABELS[filter]}
              </option>
            ))}
          </select>
        </label>
        {hasFloodDepth && (
          <label className="app-toolbar__control">
            <span>Inundation</span>
            <select
              value={floodDepthFilter}
              onChange={(e) =>
                onFloodDepthFilterChange(e.target.value as FloodDepthFilter)
              }
            >
              {(
                Object.keys(FLOOD_DEPTH_FILTER_LABELS) as FloodDepthFilter[]
              ).map((filter) => (
                <option key={filter} value={filter}>
                  {FLOOD_DEPTH_FILTER_LABELS[filter]}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="app-toolbar__control">
          <span>Point color</span>
          <select
            value={colorMode}
            onChange={(e) => onColorModeChange(e.target.value as ColorMode)}
          >
            {colorModes.map((mode) => (
              <option key={mode} value={mode}>
                {COLOR_MODE_LABELS[mode]}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}
