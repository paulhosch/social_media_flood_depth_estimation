import type { ColorMode, MapPoint, MapPointColored } from "./types";
import { inundationLevelRgba } from "./floodDepth";

const GRAY: [number, number, number, number] = [160, 160, 160, 200];
const UNIFORM: [number, number, number, number] = [37, 99, 235, 210];
const FLOODED: [number, number, number, number] = [6, 182, 212, 220];
const NON_FLOODED: [number, number, number, number] = [148, 163, 184, 200];

function parseTime(iso: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : t;
}

function datetimeColor(
  point: MapPoint,
  minMs: number,
  maxMs: number,
): [number, number, number, number] {
  const t = parseTime(point.taken_at);
  if (t === null || maxMs <= minMs) return GRAY;
  const u = (t - minMs) / (maxMs - minMs);
  const lightness = 85 - u * 55;
  return hslToRgba(215, 70, lightness, 210);
}

function densityColor(
  count: number,
  maxCount: number,
): [number, number, number, number] {
  if (maxCount <= 1) return [254, 240, 138, 210];
  const u = (count - 1) / (maxCount - 1);
  const hue = 50 - u * 50;
  const lightness = 75 - u * 45;
  return hslToRgba(hue, 85, lightness, 210);
}

function floodDepthColor(point: MapPoint): [number, number, number, number] {
  const count = point.flood_depth_vehicle_count ?? 0;
  const maxLevel = point.flood_depth_max_level;
  if (count === 0 || maxLevel === null || maxLevel === undefined) {
    return GRAY;
  }
  return inundationLevelRgba(maxLevel);
}

function hslToRgba(
  h: number,
  s: number,
  l: number,
  a: number,
): [number, number, number, number] {
  const c = (1 - Math.abs((2 * l) / 100 - 1)) * (s / 100);
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l / 100 - c / 2;
  let r = 0;
  let g = 0;
  let b = 0;
  if (h < 60) {
    r = c;
    g = x;
  } else if (h < 120) {
    r = x;
    g = c;
  } else if (h < 180) {
    g = c;
    b = x;
  } else if (h < 240) {
    g = x;
    b = c;
  } else if (h < 300) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }
  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255),
    a,
  ];
}

export function applyColors(
  points: MapPoint[],
  mode: ColorMode,
  timeRange: { min: string | null; max: string | null },
): MapPointColored[] {
  const minMs = parseTime(timeRange.min) ?? 0;
  const maxMs = parseTime(timeRange.max) ?? 0;
  const maxStack = Math.max(1, ...points.map((p) => p.stack_count));

  return points.map((point) => {
    let color: [number, number, number, number];
    switch (mode) {
      case "datetime":
        color = datetimeColor(point, minMs, maxMs);
        break;
      case "density":
        color = densityColor(point.stack_count, maxStack);
        break;
      case "flood_classification":
        color =
          point.flood_class === "flooded" ? FLOODED : NON_FLOODED;
        break;
      case "flood_depth":
        color = floodDepthColor(point);
        break;
      default:
        color = UNIFORM;
    }
    return Object.assign({}, point, { color });
  });
}

export const COLOR_MODE_LABELS: Record<ColorMode, string> = {
  uniform: "Uniform",
  datetime: "By date (lighter → earlier)",
  density: "By location density",
  flood_classification: "Flood classification",
  flood_depth: "By inundation level",
};
