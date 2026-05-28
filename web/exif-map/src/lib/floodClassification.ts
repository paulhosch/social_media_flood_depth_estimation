import type { FloodClassificationFilter, MapIndex, MapPoint } from "./types";

export function filterMapPoints(
  points: MapPoint[],
  floodClassificationFilter: FloodClassificationFilter,
): MapPoint[] {
  if (floodClassificationFilter === "all") {
    return points;
  }
  return points.filter(
    (point) => point.flood_class === floodClassificationFilter,
  );
}

export function buildFilteredMapIndex(
  index: MapIndex,
  floodClassificationFilter: FloodClassificationFilter,
): MapIndex {
  const points = filterMapPoints(index.points, floodClassificationFilter);
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

export const FLOOD_CLASSIFICATION_FILTER_LABELS: Record<
  FloodClassificationFilter,
  string
> = {
  all: "All",
  flooded: "Flooded only",
  non_flooded: "Non-flooded only",
};

export function formatFloodClass(floodClass: string): string {
  if (floodClass === "flooded") return "Flooded";
  if (floodClass === "non_flooded") return "Non-flooded";
  return floodClass;
}

export function formatFloodScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}
