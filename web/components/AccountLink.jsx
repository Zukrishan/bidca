"use client";

import { useEffect, useState } from "react";

import { clientApi, getMe } from "@/lib/client-api";

/** "Sign in" for visitors, the user's first name (→ CRA dashboard) once the auth cookie is valid. */
export function AccountLink() {
  const [user, setUser] = useState(undefined);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    getMe().then(setUser, () => setUser(null));
    clientApi("/messages/unread-count").then((d) => setUnread(d.unread || 0), () => {});
  }, []);

  if (user === undefined) return <span className="h-11 w-16" aria-hidden />;
  if (!user) {
    return (
      <a href="/login" className="inline-flex h-11 items-center rounded-lg border border-border bg-surface px-4 text-sm font-semibold hover:bg-muted">
        Sign in
      </a>
    );
  }
  return (
    <span className="inline-flex items-center">
      <a href="/messages" className="inline-flex h-11 items-center gap-1.5 px-2 text-sm font-semibold hover:underline">
        Messages
        {unread > 0 && (
          <span className="rounded-full bg-primary px-1.5 text-xs font-medium text-primary-foreground" aria-label={`${unread} unread`}>
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </a>
      <a href="/dashboard" className="inline-flex h-11 items-center px-2 text-sm font-semibold hover:underline">
        {user.full_name?.split(" ")[0] || "Account"}
      </a>
    </span>
  );
}
