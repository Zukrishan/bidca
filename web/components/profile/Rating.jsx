import { ThumbsDown, ThumbsUp } from "lucide-react";

import { cn } from "@/lib/utils";

// FR-22: green thumb = completed deal, yellow = dispute, red = failed to complete.
export const RATING_STYLES = {
  positive: { label: "Positive", className: "text-success", Icon: ThumbsUp },
  neutral: { label: "Disputed", className: "text-caution", Icon: ThumbsUp, iconClass: "-rotate-90" },
  negative: { label: "Negative", className: "text-destructive", Icon: ThumbsDown },
};

export function RatingIcon({ rating, className }) {
  const style = RATING_STYLES[rating];
  if (!style) return null;
  const { Icon } = style;
  return <Icon aria-hidden className={cn("size-4", style.className, style.iconClass, className)} />;
}

/** The three public rating counts, each with its colour. */
export function RatingSummary({ ratings }) {
  return (
    <ul className="flex flex-wrap gap-4 text-sm" aria-label="Ratings">
      {Object.entries(RATING_STYLES).map(([key, s]) => (
        <li key={key} className={cn("inline-flex items-center gap-1.5 font-medium", s.className)}>
          <RatingIcon rating={key} />
          <span className="tabular">{ratings?.[key] ?? 0}</span>
          <span className="font-normal text-muted-foreground">{s.label.toLowerCase()}</span>
        </li>
      ))}
    </ul>
  );
}
