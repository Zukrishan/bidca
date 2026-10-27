"use client";

import { useEffect } from "react";

import { clientApi, getMe } from "@/lib/client-api";

// Shared with the CRA app (same origin behind :3100), so activity in either app keeps the session.
const KEY = "bidca_last_activity";
const EVENTS = ["pointerdown", "keydown", "scroll", "touchstart", "mousemove"];

function readLast() {
  try {
    return Number(window.localStorage.getItem(KEY)) || 0;
  } catch {
    return 0;
  }
}

function writeLast(t) {
  try {
    window.localStorage.setItem(KEY, String(t));
  } catch {
    // private mode / blocked storage: the in-memory value below still works for this tab
  }
}

/**
 * Signs a signed-in user out after INACTIVITY_LOGOUT_MINUTES without input (FR-02). The API enforces
 * the same limit server-side; this makes it visible and covers a tab left open on a shared device.
 */
export function IdleLogout() {
  useEffect(() => {
    let lastLocal = Date.now();
    let interval;
    let stopped = false;
    const bump = () => {
      const now = Date.now();
      if (now - lastLocal > 5000) {
        lastLocal = now;
        writeLast(now);
      }
    };

    getMe()
      .then(async () => {
        let minutes = 30;
        try {
          const cfg = await clientApi("/auth/config");
          minutes = Number(cfg.inactivity_logout_minutes) || minutes;
        } catch {
          // keep the default
        }
        if (stopped) return;
        lastLocal = Date.now();
        writeLast(lastLocal);
        EVENTS.forEach((e) => window.addEventListener(e, bump, { passive: true }));
        interval = window.setInterval(async () => {
          const last = Math.max(lastLocal, readLast());
          if (Date.now() - last < minutes * 60 * 1000) return;
          window.clearInterval(interval);
          await clientApi("/auth/logout", { method: "POST" }).catch(() => {});
          window.location.assign("/login?reason=idle");
        }, 30 * 1000);
      })
      .catch(() => {});

    return () => {
      stopped = true;
      window.clearInterval(interval);
      EVENTS.forEach((e) => window.removeEventListener(e, bump));
    };
  }, []);

  return null;
}
