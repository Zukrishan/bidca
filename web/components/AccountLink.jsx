"use client";

import { useEffect, useState } from "react";

import { clientApi } from "@/lib/client-api";

/** "Sign in" for visitors, the user's first name (→ CRA dashboard) once the auth cookie is valid. */
export function AccountLink() {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    clientApi("/auth/me").then(setUser, () => setUser(null));
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
    <a href="/dashboard" className="inline-flex h-11 items-center px-2 text-sm font-semibold hover:underline">
      {user.full_name?.split(" ")[0] || "Account"}
    </a>
  );
}
