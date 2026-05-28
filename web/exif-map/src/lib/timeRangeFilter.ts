import type { MapIndex } from "./types";

export interface TimeRangeMs {
  start: number;
  end: number;
}

export function filterMapIndexByTimeRange(
  index: MapIndex,
  range: TimeRangeMs,
): MapIndex {
  const points = index.points.filter((point) => {
    if (!point.taken_at) return false;
    const ms = Date.parse(point.taken_at);
    if (Number.isNaN(ms)) return false;
    return ms >= range.start && ms < range.end;
  });

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

export function findBinIndexForTime(bins: { startMs: number; endMs: number }[], ms: number): number {
  return bins.findIndex((b) => ms >= b.startMs && ms < b.endMs);
}

export function timeRangeFromBinIndices(
  bins: { startMs: number; endMs: number }[],
  startIdx: number,
  endIdx: number,
): TimeRangeMs {
  const lo = Math.min(startIdx, endIdx);
  const hi = Math.max(startIdx, endIdx);
  return {
    start: bins[lo].startMs,
    end: bins[hi].endMs,
  };
}
