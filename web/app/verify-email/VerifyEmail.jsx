"use client";

import { useEffect, useState } from "react";

import { clientApi } from "@/lib/client-api";

export function VerifyEmail({ token }) {
  const [state, setState] = useState(token ? { kind: "loading" } : { kind: "error", text: "This link is missing its token." });

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    clientApi("/auth/verify-email", { method: "POST", body: { token } })
      .then(() => !cancelled && setState({ kind: "ok" }))
      .catch((err) => !cancelled && setState({ kind: "error", text: err.message }));
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (state.kind === "loading") return <p className="text-muted-foreground" role="status">Confirming your email…</p>;

  if (state.kind === "ok") {
    return (
      <>
        <p role="status" className="text-success">Email confirmed — you can now bid and sell.</p>
        <a href="/" className="flex h-12 items-center justify-center rounded-lg bg-primary px-6 text-base font-semibold text-primary-foreground hover:bg-primary-hover">
          Start browsing
        </a>
      </>
    );
  }

  return (
    <>
      <p role="alert" className="text-urgent">{state.text}</p>
      <p className="text-sm text-muted-foreground">
        Links expire after 24 hours and work once. <a href="/login" className="font-medium text-primary hover:underline">Sign in</a> and use
        &ldquo;Resend email&rdquo; on any listing to get a new one.
      </p>
    </>
  );
}
