"use client";

import { useEffect, useState } from "react";

import { formatTimeLeft, isUrgent } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Live "Ends in …" text. Server renders the value at request time; the client keeps it ticking. */
export function Countdown({ endTime, prefix = "Ends in ", className }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const label = formatTimeLeft(endTime, now);
  return (
    <span
      suppressHydrationWarning
      className={cn("tabular", isUrgent(endTime, now) && "font-semibold text-urgent", className)}
    >
      {label === "Ended" ? label : `${prefix}${label}`}
    </span>
  );
}
