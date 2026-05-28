export interface ToolbarSummaryInput {
  totalCount: number;
  filteredCount: number;
  timeRange: { min: string | null; max: string | null };
  timeBrushRange?: { start: number; end: number } | null;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatToolbarSummary(input: ToolbarSummaryInput): string {
  const { totalCount, filteredCount, timeRange, timeBrushRange } = input;

  let text =
    filteredCount === totalCount
      ? `${filteredCount.toLocaleString()} images`
      : `${filteredCount.toLocaleString()} images of ${totalCount.toLocaleString()}`;

  if (timeBrushRange) {
    text += ` · ${formatDate(new Date(timeBrushRange.start).toISOString())} – ${formatDate(new Date(timeBrushRange.end - 1).toISOString())} (time filtered)`;
  } else if (timeRange.min && timeRange.max) {
    text += ` · ${formatDate(timeRange.min)} – ${formatDate(timeRange.max)}`;
  }

  return text;
}

export function binUnitLabel(unit: string): string {
  switch (unit) {
    case "day":
      return "Daily bins";
    case "week":
      return "Weekly bins";
    case "month":
      return "Monthly bins";
    case "year":
      return "Yearly bins";
    default:
      return "Bins";
  }
}

export function formatHistogramSummary(
  unitLabel: string,
  peakCount: number,
  peakLabel: string,
): string {
  return `${unitLabel} · peak ${peakCount.toLocaleString()} · ${peakLabel}`;
}
