import React, { useEffect, useRef } from "react";

// Cloudflare Turnstile CAPTCHA on sign-up and login (FR-01, FR-02). The site key comes from
// GET /auth/config; without one (dev) nothing renders and the API skips the check.
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
let scriptPromise;

function loadTurnstile() {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = SCRIPT_SRC;
      s.async = true;
      s.onload = () => resolve(window.turnstile);
      s.onerror = () => {
        scriptPromise = undefined;
        reject(new Error("CAPTCHA failed to load"));
      };
      document.head.appendChild(s);
    });
  }
  return scriptPromise;
}

/** Renders the widget and reports the token ("" when it expires). Change `resetKey` to get a fresh token. */
export default function Turnstile({ siteKey, onToken, resetKey = 0 }) {
  const ref = useRef(null);
  const onTokenRef = useRef(onToken);
  onTokenRef.current = onToken;

  useEffect(() => {
    if (!siteKey) return undefined;
    let widgetId;
    let cancelled = false;
    onTokenRef.current("");
    loadTurnstile()
      .then((turnstile) => {
        if (cancelled || !ref.current) return;
        widgetId = turnstile.render(ref.current, {
          sitekey: siteKey,
          callback: (token) => onTokenRef.current(token),
          "expired-callback": () => onTokenRef.current(""),
          "error-callback": () => onTokenRef.current(""),
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (widgetId !== undefined && window.turnstile) window.turnstile.remove(widgetId);
    };
  }, [siteKey, resetKey]);

  if (!siteKey) return null;
  return <div ref={ref} className="min-h-[65px]" data-testid="captcha" />;
}
