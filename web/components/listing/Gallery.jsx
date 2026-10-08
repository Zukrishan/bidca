"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";

/** Main square photo plus thumbnails. Plain img: seller photos come from arbitrary hosts. */
export function Gallery({ images, title }) {
  const [index, setIndex] = useState(0);
  if (!images?.length) {
    return <div className="aspect-square rounded-lg border border-border bg-muted" aria-label="No photo" />;
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="aspect-square overflow-hidden rounded-lg border border-border bg-muted">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={images[index]} alt={title} className="h-full w-full object-cover" fetchPriority="high" />
      </div>
      {images.length > 1 && (
        <ul className="flex flex-wrap gap-2">
          {images.map((src, i) => (
            <li key={src + i}>
              <button
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`Show photo ${i + 1}`}
                aria-current={i === index}
                className={cn(
                  "size-16 overflow-hidden rounded-lg border bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  i === index ? "border-primary" : "border-border"
                )}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={src} alt="" loading="lazy" className="h-full w-full object-cover" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
