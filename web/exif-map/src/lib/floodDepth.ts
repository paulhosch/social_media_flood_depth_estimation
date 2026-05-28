import type { FloodDepthFilter, MapIndex, MapPoint } from "./types";

export function mapHasFloodDepth(index: MapIndex): boolean {
  return index.points.some((point) => point.flood_depth_detections !== undefined);
}

export function filterMapPointsByDepth(
  points: MapPoint[],
  floodDepthFilter: FloodDepthFilter,
): MapPoint[] {
  if (floodDepthFilter === "all") {
    return points;
  }

  return points.filter((point) => {
    const count = point.flood_depth_vehicle_count ?? 0;
    const highDanger = point.flood_depth_high_danger ?? false;

    switch (floodDepthFilter) {
      case "has_vehicles":
        return count > 0;
      case "high_danger":
        return highDanger;
      case "no_vehicles":
        return count === 0;
      default:
        return true;
    }
  });
}

export function buildDepthFilteredMapIndex(
  index: MapIndex,
  floodDepthFilter: FloodDepthFilter,
): MapIndex {
  const points = filterMapPointsByDepth(index.points, floodDepthFilter);
  const takenMs = points
    .map((point) => point.taken_at)
    .filter((value): value is string => value != null)
    .map((iso) => Date.parse(iso))
    .filter((ms) => !Number.isNaN(ms));

  let time_range = { min: null as string | null, max: null as string | null };
  if (takenMs.length > 0) {
    const minMs = Math.min(...takenMs);
    const maxMs = Math.max(...takenMs);
    time_range = {
      min: new Date(minMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
      max: new Date(maxMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    };
  }

  return {
    ...index,
    point_count: points.length,
    time_range,
    points,
  };
}

export const FLOOD_DEPTH_FILTER_LABELS: Record<FloodDepthFilter, string> = {
  all: "All",
  has_vehicles: "Has vehicles",
  high_danger: "High danger (L3–L4)",
  no_vehicles: "No vehicles",
};

/** L0 green, L1–L2 yellow, L3–L4 red */
const INUNDATION_LEVEL_COLORS: Record<
  number,
  { hex: string; rgba: [number, number, number, number] }
> = {
  0: { hex: "#22c55e", rgba: [34, 197, 94, 220] },
  1: { hex: "#eab308", rgba: [234, 179, 8, 220] },
  2: { hex: "#eab308", rgba: [234, 179, 8, 220] },
  3: { hex: "#ef4444", rgba: [239, 68, 68, 220] },
  4: { hex: "#ef4444", rgba: [239, 68, 68, 220] },
};

export function inundationLevelHex(level: number): string {
  return INUNDATION_LEVEL_COLORS[level]?.hex ?? "#94a3b8";
}

export function inundationLevelRgba(
  level: number,
): [number, number, number, number] {
  return INUNDATION_LEVEL_COLORS[level]?.rgba ?? [148, 163, 184, 200];
}

function inundationLevelGroup(level: number): "l0" | "l1-2" | "l3-4" | "unknown" {
  if (level === 0) return "l0";
  if (level >= 1 && level <= 2) return "l1-2";
  if (level >= 3 && level <= 4) return "l3-4";
  return "unknown";
}

export function inundationLevelChipClass(level: number): string {
  return `side-panel__level-chip side-panel__level-chip--${inundationLevelGroup(level)}`;
}

export function inundationLevelValueClass(level: number): string {
  return `side-panel__value--inundation-${inundationLevelGroup(level)}`;
}

export function formatInundationLevel(level: number | null | undefined): string {
  if (level === null || level === undefined) {
    return "No vehicles";
  }
  return `Level ${level}`;
}

export function levelCountsFromDetections(
  detections: MapPoint["flood_depth_detections"],
): Record<number, number> {
  const counts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };
  for (const detection of detections ?? []) {
    counts[detection.level] = (counts[detection.level] ?? 0) + 1;
  }
  return counts;
}
