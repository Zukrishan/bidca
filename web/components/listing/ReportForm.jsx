"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clientApi, getMe } from "@/lib/client-api";

const REASONS = ["Spam or scam", "Prohibited item", "Wrong category", "Misleading description", "Other"];

/** Tiny report disclosure. Visitors are sent to /login instead. */
export function ReportForm({ listingId }) {
  const [user, setUser] = useState(undefined);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState(REASONS[0]);
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState(null);

  useEffect(() => {
    getMe().then(setUser, () => setUser(null));
  }, []);

  if (user === undefined) return null;
  if (!user) {
    return (
      <a href="/login" className="text-sm text-muted-foreground underline hover:text-foreground">
        Sign in to report this listing
      </a>
    );
  }
  if (status?.ok) return <p className="text-sm text-muted-foreground">{status.text}</p>;

  async function submit(e) {
    e.preventDefault();
    try {
      const r = await clientApi(`/listings/${listingId}/report`, { method: "POST", body: { reason, description: description || reason } });
      setStatus({ ok: true, text: r.message || "Thanks, we'll take a look." });
    } catch (err) {
      setStatus({ ok: false, text: err.message });
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="text-sm text-muted-foreground underline hover:text-foreground">
        Report this listing
      </button>
    );
  }
  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-2">
      <select value={reason} onChange={(e) => setReason(e.target.value)} className="h-11 rounded-lg border border-border bg-surface px-3 text-base" aria-label="Reason">
        {REASONS.map((r) => (
          <option key={r}>{r}</option>
        ))}
      </select>
      <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Details (optional)" aria-label="Details" />
      {status && !status.ok && <p role="alert" className="text-sm text-urgent">{status.text}</p>}
      <div className="flex gap-2">
        <Button type="submit" size="sm">Send report</Button>
        <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </form>
  );
}
