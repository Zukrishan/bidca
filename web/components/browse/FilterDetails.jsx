"use client";

import { useEffect, useRef } from "react";

/**
 * Filter panel: open in the server HTML (works without JS and on desktop, where the summary is
 * hidden), collapsed on mobile once hydrated.
 */
export function FilterDetails({ summary, children }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && window.matchMedia("(max-width: 1023px)").matches) ref.current.open = false;
  }, []);
  return (
    <details ref={ref} open className="rounded-lg border border-border bg-surface lg:border-0 lg:bg-transparent">
      <summary className="flex h-11 cursor-pointer items-center px-3 text-sm font-semibold lg:hidden">{summary}</summary>
      <div className="p-3 pt-1 lg:p-0">{children}</div>
    </details>
  );
}
