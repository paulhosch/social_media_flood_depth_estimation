import { useCallback, useEffect, useRef, useState } from "react";

interface PanelResizerProps {
  panelWidth: number;
  onResize: (width: number) => void;
}

export default function PanelResizer({
  panelWidth,
  onResize,
}: PanelResizerProps) {
  const [active, setActive] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(panelWidth);

  const onPointerDown = useCallback(
    (event: React.PointerEvent) => {
      event.preventDefault();
      startXRef.current = event.clientX;
      startWidthRef.current = panelWidth;
      setActive(true);
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    },
    [panelWidth],
  );

  useEffect(() => {
    if (!active) return;

    const onPointerMove = (event: PointerEvent) => {
      const delta = startXRef.current - event.clientX;
      onResize(startWidthRef.current + delta);
    };

    const onPointerUp = () => {
      setActive(false);
    };

    document.addEventListener("pointermove", onPointerMove);
    document.addEventListener("pointerup", onPointerUp);
    return () => {
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp);
    };
  }, [active, onResize]);

  return (
    <div
      className={
        active ? "panel-resizer panel-resizer--active" : "panel-resizer"
      }
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize side panel"
      onPointerDown={onPointerDown}
    />
  );
}
