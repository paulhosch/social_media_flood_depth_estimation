import { useEffect } from "react";
import type { FloodDepthDetection } from "../lib/types";
import ImageWithDetections from "./ImageWithDetections";

interface ImageLightboxProps {
  src: string;
  alt: string;
  detections?: FloodDepthDetection[];
  showDetections: boolean;
  onClose: () => void;
}

export default function ImageLightbox({
  src,
  alt,
  detections = [],
  showDetections,
  onClose,
}: ImageLightboxProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div
      className="image-lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="Enlarged image"
      onClick={onClose}
    >
      <button
        type="button"
        className="image-lightbox__close"
        aria-label="Close enlarged image"
        onClick={onClose}
      >
        ×
      </button>
      <div
        className="image-lightbox__content"
        onClick={(event) => event.stopPropagation()}
      >
        {showDetections ? (
          <ImageWithDetections
            src={src}
            alt={alt}
            detections={detections}
            imageClassName="image-lightbox__image"
          />
        ) : (
          <img className="image-lightbox__image" src={src} alt={alt} />
        )}
      </div>
    </div>
  );
}
