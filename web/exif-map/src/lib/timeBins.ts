export type BinUnit = "day" | "week" | "month" | "year";

export interface TimeBin {
  startMs: number;
  endMs: number;
  count: number;
  label: string;
}

const MS_DAY = 86_400_000;

function startOfUtcDay(ms: number): number {
  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}

function startOfUtcMonth(ms: number): number {
  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1);
}

function startOfUtcYear(ms: number): number {
  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear(), 0, 1);
}

function addMonthsUtc(ms: number, months: number): number {
  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months, 1);
}

function addYearsUtc(ms: number, years: number): number {
  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear() + years, 0, 1);
}

export function chooseBinUnit(minMs: number, maxMs: number): BinUnit {
  const spanDays = (maxMs - minMs) / MS_DAY;
  if (spanDays <= 90) return "day";
  if (spanDays <= 730) return "week";
  if (spanDays <= 3650) return "month";
  return "year";
}

function binStart(ms: number, unit: BinUnit): number {
  switch (unit) {
    case "day":
      return startOfUtcDay(ms);
    case "week": {
      const day = startOfUtcDay(ms);
      const d = new Date(day);
      const dow = d.getUTCDay();
      const diff = dow === 0 ? 6 : dow - 1;
      return day - diff * MS_DAY;
    }
    case "month":
      return startOfUtcMonth(ms);
    case "year":
      return startOfUtcYear(ms);
  }
}

function nextBinStart(ms: number, unit: BinUnit): number {
  switch (unit) {
    case "day":
      return ms + MS_DAY;
    case "week":
      return ms + 7 * MS_DAY;
    case "month":
      return addMonthsUtc(ms, 1);
    case "year":
      return addYearsUtc(ms, 1);
  }
}

function formatBinLabel(startMs: number, unit: BinUnit): string {
  const d = new Date(startMs);
  switch (unit) {
    case "day":
      return d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    case "week":
      return `Week of ${d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
    case "month":
      return d.toLocaleDateString(undefined, { year: "numeric", month: "short" });
    case "year":
      return String(d.getUTCFullYear());
  }
}

export function buildTimeBins(
  takenAtIso: (string | null)[],
  timeRange: { min: string | null; max: string | null },
  unitOverride?: BinUnit,
): TimeBin[] {
  const times = takenAtIso
    .map((iso) => (iso ? Date.parse(iso) : NaN))
    .filter((t) => !Number.isNaN(t));
  if (times.length === 0) return [];

  const minMs = timeRange.min
    ? Date.parse(timeRange.min)
    : Math.min(...times);
  const maxMs = timeRange.max
    ? Date.parse(timeRange.max)
    : Math.max(...times);
  if (Number.isNaN(minMs) || Number.isNaN(maxMs) || maxMs < minMs) {
    return [];
  }

  const unit = unitOverride ?? chooseBinUnit(minMs, maxMs);
  const bins: TimeBin[] = [];
  let cursor = binStart(minMs, unit);
  const endLimit = binStart(maxMs, unit);

  while (cursor <= endLimit) {
    const end = nextBinStart(cursor, unit);
    bins.push({
      startMs: cursor,
      endMs: end,
      count: 0,
      label: formatBinLabel(cursor, unit),
    });
    cursor = end;
  }

  for (const t of times) {
    const idx = bins.findIndex((b) => t >= b.startMs && t < b.endMs);
    if (idx >= 0) bins[idx].count += 1;
  }

  return bins;
}

export function pickTickIndices(binCount: number, maxTicks = 7): number[] {
  if (binCount <= maxTicks) {
    return Array.from({ length: binCount }, (_, i) => i);
  }
  const step = Math.ceil(binCount / maxTicks);
  const indices: number[] = [];
  for (let i = 0; i < binCount; i += step) indices.push(i);
  if (indices[indices.length - 1] !== binCount - 1) {
    indices.push(binCount - 1);
  }
  return indices;
}
