import { useCallback, useMemo, useRef, useState } from "react";
import type { MapIndex } from "../lib/types";
import {
  binUnitLabel,
  formatHistogramSummary,
} from "../lib/timelineSummary";
import {
  findBinIndexForTime,
  timeRangeFromBinIndices,
  type TimeRangeMs,
} from "../lib/timeRangeFilter";
import { useElementSize } from "../lib/useElementSize";
import {
  buildTimeBins,
  pickTickIndices,
  type BinUnit,
  type TimeBin,
} from "../lib/timeBins";

interface TimeHistogramProps {
  index: MapIndex;
  selectedTakenAt?: string | null;
  timeRangeMs: TimeRangeMs | null;
  onTimeRangeChange: (range: TimeRangeMs | null) => void;
}

const HEIGHT = 120;
const PAD = { top: 28, right: 12, bottom: 28, left: 36 };
const BAR_GAP = 2;
const BAR_RX = 2;

function binIndicesForRange(
  bins: TimeBin[],
  range: TimeRangeMs,
): { start: number; end: number } | null {
  const start = findBinIndexForTime(bins, range.start);
  let end = findBinIndexForTime(bins, range.end - 1);
  if (end < 0 && range.end > bins[bins.length - 1]?.startMs) {
    end = bins.length - 1;
  }
  if (start < 0) return null;
  return { start, end: Math.max(start, end) };
}

export default function TimeHistogram({
  index,
  selectedTakenAt,
  timeRangeMs,
  onTimeRangeChange,
}: TimeHistogramProps) {
  const { ref, width } = useElementSize<HTMLDivElement>();
  const svgRef = useRef<SVGSVGElement>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [dragging, setDragging] = useState<
    | { kind: "new"; anchorIdx: number; currentIdx: number }
    | { kind: "handle"; edge: "start" | "end"; anchorIdx: number }
    | null
  >(null);

  const bins = useMemo(
    () =>
      buildTimeBins(
        index.points.map((p) => p.taken_at),
        index.time_range,
        "day",
      ),
    [index],
  );

  const binUnit: BinUnit = "day";

  const maxCount = useMemo(
    () => Math.max(1, ...bins.map((b) => b.count)),
    [bins],
  );

  const peakBin = useMemo(() => {
    if (bins.length === 0) return null;
    return bins.reduce((best, b) => (b.count > best.count ? b : best), bins[0]);
  }, [bins]);

  const tickIndices = useMemo(() => pickTickIndices(bins.length), [bins.length]);

  const brushIndices = useMemo(() => {
    if (!timeRangeMs || bins.length === 0) return null;
    return binIndicesForRange(bins, timeRangeMs);
  }, [bins, timeRangeMs]);

  const selectedBinIdx = useMemo(() => {
    if (!selectedTakenAt) return -1;
    const ms = Date.parse(selectedTakenAt);
    if (Number.isNaN(ms)) return -1;
    return findBinIndexForTime(bins, ms);
  }, [bins, selectedTakenAt]);

  const chartWidth = Math.max(width, 200);
  const chartW = chartWidth - PAD.left - PAD.right;
  const chartH = HEIGHT - PAD.top - PAD.bottom;
  const barW = bins.length > 0 ? chartW / bins.length : 0;

  const clientXToBinIndex = useCallback(
    (clientX: number): number => {
      const svg = svgRef.current;
      if (!svg || bins.length === 0) return 0;
      const rect = svg.getBoundingClientRect();
      const x = ((clientX - rect.left) / rect.width) * chartWidth;
      const rel = x - PAD.left;
      const idx = Math.floor(rel / barW);
      return Math.max(0, Math.min(bins.length - 1, idx));
    },
    [bins.length, barW, chartWidth],
  );

  const finishDrag = useCallback(
    (startIdx: number, endIdx: number) => {
      onTimeRangeChange(timeRangeFromBinIndices(bins, startIdx, endIdx));
    },
    [bins, onTimeRangeChange],
  );

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (bins.length === 0) return;
      const idx = clientXToBinIndex(e.clientX);
      const target = e.target as Element;
      if (target.classList.contains("time-histogram__handle")) {
        const edge = target.getAttribute("data-edge") as "start" | "end";
        setDragging({ kind: "handle", edge, anchorIdx: idx });
      } else {
        setDragging({ kind: "new", anchorIdx: idx, currentIdx: idx });
      }
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    },
    [bins.length, clientXToBinIndex],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging) return;
      const idx = clientXToBinIndex(e.clientX);
      if (dragging.kind === "new") {
        setDragging({ ...dragging, currentIdx: idx });
      } else if (dragging.kind === "handle" && brushIndices) {
        const { start, end } = brushIndices;
        if (dragging.edge === "start") {
          finishDrag(Math.min(idx, end), end);
        } else {
          finishDrag(start, Math.max(idx, start));
        }
      }
    },
    [dragging, clientXToBinIndex, brushIndices, finishDrag],
  );

  const onPointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging) return;
      if (dragging.kind === "new") {
        const idx = clientXToBinIndex(e.clientX);
        const lo = Math.min(dragging.anchorIdx, idx);
        const hi = Math.max(dragging.anchorIdx, idx);
        if (lo === hi) {
          onTimeRangeChange(timeRangeFromBinIndices(bins, lo, lo));
        } else {
          finishDrag(dragging.anchorIdx, idx);
        }
      }
      setDragging(null);
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    },
    [dragging, clientXToBinIndex, finishDrag, bins, onTimeRangeChange],
  );

  const isSingleDaySelected = (i: number): boolean =>
    brushIndices !== null &&
    brushIndices.start === brushIndices.end &&
    brushIndices.start === i;

  const isBarInBrush = (i: number): boolean => {
    if (dragging?.kind === "new") {
      const lo = Math.min(dragging.anchorIdx, dragging.currentIdx);
      const hi = Math.max(dragging.anchorIdx, dragging.currentIdx);
      return i >= lo && i <= hi;
    }
    if (!brushIndices) return true;
    return i >= brushIndices.start && i <= brushIndices.end;
  };

  if (bins.length === 0) {
    return (
      <div className="time-histogram time-histogram--empty">
        No dated images for timeline
      </div>
    );
  }

  const summaryText =
    peakBin &&
    formatHistogramSummary(
      binUnitLabel(binUnit),
      peakBin.count,
      peakBin.label,
    );

  const brushOverlay = brushIndices
    ? {
        x: PAD.left + brushIndices.start * barW,
        width:
          PAD.left +
          (brushIndices.end + 1) * barW -
          (PAD.left + brushIndices.start * barW),
      }
    : null;

  const dragOverlay =
    dragging?.kind === "new"
      ? (() => {
          const lo = Math.min(dragging.anchorIdx, dragging.currentIdx);
          const hi = Math.max(dragging.anchorIdx, dragging.currentIdx);
          const x0 = PAD.left + lo * barW;
          const x1 = PAD.left + (hi + 1) * barW;
          return { x: x0, width: x1 - x0 };
        })()
      : null;

  const rangeOverlay = dragOverlay ?? brushOverlay;

  return (
    <section className="time-histogram">
      <div className="time-histogram__header">
        {summaryText && (
          <p className="time-histogram__summary">{summaryText}</p>
        )}
        {timeRangeMs && (
          <button
            type="button"
            className="time-histogram__clear"
            onClick={() => onTimeRangeChange(null)}
          >
            Clear time filter
          </button>
        )}
      </div>
      <div ref={ref} className="time-histogram__chart-wrap">
        <svg
          ref={svgRef}
          width="100%"
          height={HEIGHT}
          viewBox={`0 0 ${chartWidth} ${HEIGHT}`}
          className="time-histogram__svg"
          role="img"
          aria-label="Image count over time"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        >
          <text
            x={PAD.left}
            y={PAD.top - 10}
            className="time-histogram__max-label"
          >
            {maxCount}
          </text>
          {[0.25, 0.5, 0.75].map((frac) => (
            <line
              key={frac}
              x1={PAD.left}
              x2={chartWidth - PAD.right}
              y1={PAD.top + chartH * (1 - frac)}
              y2={PAD.top + chartH * (1 - frac)}
              className="time-histogram__grid"
            />
          ))}
          <line
            x1={PAD.left}
            x2={chartWidth - PAD.right}
            y1={PAD.top + chartH}
            y2={PAD.top + chartH}
            className="time-histogram__baseline"
          />
          {rangeOverlay && (
            <rect
              x={rangeOverlay.x}
              y={PAD.top}
              width={rangeOverlay.width}
              height={chartH}
              className="time-histogram__brush-fill"
            />
          )}
          {bins.map((bin, i) => {
            const h = (bin.count / maxCount) * chartH;
            const x = PAD.left + i * barW;
            const y = PAD.top + chartH - h;
            const isHovered = hovered === i;
            const inBrush = isBarInBrush(i);
            const w = Math.max(1, barW - BAR_GAP);
            return (
              <g
                key={bin.startMs}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className="time-histogram__bar-group"
              >
                <rect
                  x={x + BAR_GAP / 2}
                  y={y}
                  width={w}
                  height={h}
                  rx={BAR_RX}
                  className={
                    isSingleDaySelected(i)
                      ? "time-histogram__bar time-histogram__bar--selected"
                      : isHovered
                        ? "time-histogram__bar time-histogram__bar--hover"
                        : inBrush
                          ? "time-histogram__bar"
                          : "time-histogram__bar time-histogram__bar--dim"
                  }
                />
              </g>
            );
          })}
          {selectedBinIdx >= 0 && (
            <line
              x1={PAD.left + selectedBinIdx * barW + barW / 2}
              x2={PAD.left + selectedBinIdx * barW + barW / 2}
              y1={PAD.top}
              y2={PAD.top + chartH}
              className="time-histogram__marker"
            />
          )}
          {brushIndices && !dragging && (
            <>
              <rect
                x={PAD.left + brushIndices.start * barW - 3}
                y={PAD.top}
                width={6}
                height={chartH}
                className="time-histogram__handle"
                data-edge="start"
              />
              <rect
                x={PAD.left + (brushIndices.end + 1) * barW - 3}
                y={PAD.top}
                width={6}
                height={chartH}
                className="time-histogram__handle"
                data-edge="end"
              />
            </>
          )}
          {tickIndices.map((i) => {
            const x = PAD.left + i * barW + barW / 2;
            return (
              <text
                key={bins[i].startMs}
                x={x}
                y={HEIGHT - 6}
                textAnchor="middle"
                className="time-histogram__tick"
              >
                {bins[i].label}
              </text>
            );
          })}
        </svg>
        {hovered !== null && barW > 0 && (
          <div
            className="time-histogram__tooltip"
            style={{
              left: `${((PAD.left + hovered * barW + barW / 2) / chartWidth) * 100}%`,
            }}
          >
            {bins[hovered].label} · {bins[hovered].count} image
            {bins[hovered].count === 1 ? "" : "s"}
          </div>
        )}
      </div>
    </section>
  );
}
