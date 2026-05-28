import { useId, useMemo, useState } from "react";

const COLLAPSED_LINES = 3;

interface ExpandableTextProps {
  text: string;
  className?: string;
}

export default function ExpandableText({ text, className }: ExpandableTextProps) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();

  const needsToggle = useMemo(() => {
    const lineCount = text.split(/\r?\n/).length;
    return text.length > 160 || lineCount > COLLAPSED_LINES;
  }, [text]);

  return (
    <div className={className ? `expandable-text ${className}` : "expandable-text"}>
      <p
        id={contentId}
        className={
          expanded || !needsToggle
            ? "expandable-text__content"
            : "expandable-text__content expandable-text__content--collapsed"
        }
      >
        {text}
      </p>
      {needsToggle && (
        <button
          type="button"
          className="expandable-text__toggle"
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
