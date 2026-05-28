import { useCallback, useEffect, useRef } from "react";
import { inundationLevelHex } from "../lib/floodDepth";
import type { FloodDepthDetection } from "../lib/types";

interface ImageWithDetectionsProps {
  src: string;
  alt: string;
  detections: FloodDepthDetection[];
  imageClassName?: string;
}

export default function ImageWithDetections({
  src,
  alt,
  detections,
  imageClassName = "side-panel__image",
}: ImageWithDetectionsProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const drawOverlay = useCallback(() => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas || detections.length === 0) {
      return;
    }

    const displayWidth = img.clientWidth;
    const displayHeight = img.clientHeight;
    if (displayWidth === 0 || displayHeight === 0) {
      return;
    }

    const naturalWidth = img.naturalWidth;
    const naturalHeight = img.naturalHeight;
    if (naturalWidth === 0 || naturalHeight === 0) {
      return;
    }

    canvas.width = displayWidth;
    canvas.height = displayHeight;
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    ctx.clearRect(0, 0, displayWidth, displayHeight);
    const scaleX = displayWidth / naturalWidth;
    const scaleY = displayHeight / naturalHeight;

    for (const detection of detections) {
      const [x1, y1, x2, y2] = detection.bbox;
      const left = x1 * scaleX;
      const top = y1 * scaleY;
      const width = (x2 - x1) * scaleX;
      const height = (y2 - y1) * scaleY;
      const color = inundationLevelHex(detection.level);

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(left, top, width, height);

      const label = `Level ${detection.level}: ${detection.confidence.toFixed(2)}`;
      ctx.font = "12px system-ui, sans-serif";
      const metrics = ctx.measureText(label);
      const labelHeight = 16;
      const labelY = Math.max(top - 4, labelHeight);

      ctx.fillStyle = color;
      ctx.fillRect(left, labelY - labelHeight, metrics.width + 8, labelHeight + 4);
      ctx.fillStyle = "#ffffff";
      ctx.fillText(label, left + 4, labelY);
    }
  }, [detections]);

  useEffect(() => {
    drawOverlay();
  }, [drawOverlay, src]);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) {
      return;
    }

    const observer = new ResizeObserver(() => {
      drawOverlay();
    });
    observer.observe(img);
    return () => observer.disconnect();
  }, [drawOverlay]);

  return (
    <div className="image-with-detections">
      <img
        ref={imgRef}
        className={imageClassName}
        src={src}
        alt={alt}
        onLoad={drawOverlay}
      />
      {detections.length > 0 && (
        <canvas
          ref={canvasRef}
          className="image-with-detections__canvas"
          aria-hidden
        />
      )}
      {detections.length === 0 && (
        <p className="image-with-detections__empty">No vehicles detected</p>
      )}
    </div>
  );
}
