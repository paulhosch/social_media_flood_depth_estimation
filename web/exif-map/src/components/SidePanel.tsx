import { useCallback, useEffect, useState } from "react";
import {
  formatFloodClass,
  formatFloodScore,
} from "../lib/floodClassification";
import {
  formatInundationLevel,
  inundationLevelChipClass,
  inundationLevelValueClass,
  levelCountsFromDetections,
} from "../lib/floodDepth";
import type { MapPoint } from "../lib/types";
import { formatCoord, formatDateTime, imageUrl } from "../lib/format";
import ExpandableText from "./ExpandableText";
import ImageLightbox from "./ImageLightbox";
import ImageWithDetections from "./ImageWithDetections";

interface SidePanelProps {
  point: MapPoint | null;
  hasFloodDepth: boolean;
  width: number;
}

export default function SidePanel({
  point,
  hasFloodDepth,
  width,
}: SidePanelProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const openLightbox = useCallback(() => setLightboxOpen(true), []);
  const closeLightbox = useCallback(() => setLightboxOpen(false), []);

  useEffect(() => {
    setLightboxOpen(false);
  }, [point?.file_name]);

  if (!point) {
    return (
      <aside className="side-panel" style={{ width }}>
        <div className="side-panel__empty">
          <p className="side-panel__hint">Click a point on the map</p>
        </div>
      </aside>
    );
  }

  const detections = point.flood_depth_detections ?? [];
  const levelCounts = levelCountsFromDetections(detections);
  const showDepth = hasFloodDepth && point.flood_depth_detections !== undefined;
  const src = imageUrl(point.file_name);

  return (
    <>
      <aside className="side-panel" style={{ width }}>
        <button
          type="button"
          className="side-panel__image-wrap"
          onClick={openLightbox}
          aria-label="Enlarge image"
        >
          {showDepth ? (
            <ImageWithDetections
              src={src}
              alt={point.file_name}
              detections={detections}
            />
          ) : (
            <img
              className="side-panel__image"
              src={src}
              alt={point.file_name}
            />
          )}
          <span className="side-panel__zoom-hint">Click to enlarge</span>
        </button>

        <div className="side-panel__meta">
          <section className="side-panel__section">
            <h3 className="side-panel__section-title">Post details</h3>
            <MetaRow label="File name" value={point.file_name} mono />
            <MetaRow label="Platform" value={point.platform || "—"} />
            <MetaRow label="Post ID" value={point.post_id || "—"} mono />
            {point.tags.length > 0 && (
              <div className="side-panel__field">
                <dt>Tags</dt>
                <dd className="side-panel__tags">
                  {point.tags.map((tag) => (
                    <span key={tag} className="side-panel__tag">
                      {tag}
                    </span>
                  ))}
                </dd>
              </div>
            )}
            {point.caption && (
              <div className="side-panel__field side-panel__field--block">
                <dt>Caption</dt>
                <dd>
                  <ExpandableText text={point.caption} />
                </dd>
              </div>
            )}
          </section>

          <section className="side-panel__section">
            <h3 className="side-panel__section-title">EXIF & location</h3>
            <MetaRow
              label="DateTime (original)"
              value={formatDateTime(point.exif_taken_at_original)}
            />
            <MetaRow
              label="DateTime (record)"
              value={formatDateTime(point.exif_taken_at_record)}
            />
            <div className="side-panel__grid">
              <MetaRow label="Latitude" value={formatCoord(point.lat)} mono />
              <MetaRow label="Longitude" value={formatCoord(point.lon)} mono />
            </div>
          </section>

          <section className="side-panel__section">
            <h3 className="side-panel__section-title">Flood classification</h3>
            <MetaRow
              label="Flood class"
              value={formatFloodClass(point.flood_class)}
              highlight={
                point.flood_class === "flooded" ? "danger" : "neutral"
              }
            />
            <div className="side-panel__grid">
              <MetaRow
                label="P(flooded)"
                value={formatFloodScore(point.flood_score_flooded)}
              />
              <MetaRow
                label="P(non-flooded)"
                value={formatFloodScore(point.flood_score_non_flooded)}
              />
            </div>
          </section>

          {showDepth && (
            <section className="side-panel__section">
              <h3 className="side-panel__section-title">Vehicle inundation</h3>
              {point.flood_depth_high_danger && (
                <p className="side-panel__danger">High danger (Level 3 or 4)</p>
              )}
              <div className="side-panel__grid">
                <MetaRow
                  label="Max level"
                  value={formatInundationLevel(point.flood_depth_max_level)}
                  inundationLevel={point.flood_depth_max_level ?? undefined}
                />
                <MetaRow
                  label="Vehicles"
                  value={String(point.flood_depth_vehicle_count ?? 0)}
                />
              </div>
              <div className="side-panel__level-grid">
                {[0, 1, 2, 3, 4].map((level) => (
                  <div key={level} className={inundationLevelChipClass(level)}>
                    <span className="side-panel__level-label">L{level}</span>
                    <span className="side-panel__level-value">
                      {levelCounts[level] ?? 0}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </aside>

      {lightboxOpen && (
        <ImageLightbox
          src={src}
          alt={point.file_name}
          detections={detections}
          showDetections={showDepth}
          onClose={closeLightbox}
        />
      )}
    </>
  );
}

function MetaRow({
  label,
  value,
  mono = false,
  highlight,
  inundationLevel,
}: {
  label: string;
  value: string;
  mono?: boolean;
  highlight?: "danger" | "neutral";
  inundationLevel?: number;
}) {
  const levelClass =
    inundationLevel !== undefined
      ? inundationLevelValueClass(inundationLevel)
      : "";

  return (
    <div className="side-panel__field">
      <dt>{label}</dt>
      <dd
        className={[
          mono ? "side-panel__value--mono" : "",
          highlight === "danger" ? "side-panel__value--danger" : "",
          highlight === "neutral" ? "side-panel__value--neutral" : "",
          levelClass,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {value}
      </dd>
    </div>
  );
}
