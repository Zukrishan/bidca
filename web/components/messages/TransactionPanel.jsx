"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/client-api";
import { formatCAD } from "@/lib/format";
import { cn } from "@/lib/utils";

// FR-24/FR-25: the deal itself — order summary, Complete (both sides), Dispute with proof, rating.
// BidCa never handles money, so nothing here mentions paying.

const STATUS = {
  open: { label: "Open", variant: "default" },
  completed: { label: "Completed", variant: "success" },
  disputed: { label: "Disputed", variant: "urgent" },
  cancelled: { label: "Cancelled", variant: "default" },
};

const EXCHANGE = {
  cash: "Cash on pickup",
  cash_on_pickup: "Cash on pickup",
  e_transfer: "e-Transfer",
  etransfer: "e-Transfer",
  meet_public: "Meet in a public place",
  meet_in_public: "Meet in a public place",
};

const RATINGS = [
  { value: "positive", emoji: "👍", label: "Good", className: "text-success" },
  { value: "neutral", emoji: "🟡", label: "Problem, but sorted", className: "text-foreground" },
  { value: "negative", emoji: "👎", label: "Fell through", className: "text-destructive" },
];

const MAX_PROOFS = 10;

/** Upload one file to Cloudinary with a signature from our API; resolves the hosted URL. */
async function uploadProof(file) {
  const sig = await clientApi("/cloudinary/signature?folder=bidca_disputes");
  const form = new FormData();
  form.append("file", file);
  form.append("api_key", sig.api_key);
  form.append("timestamp", String(sig.timestamp));
  form.append("signature", sig.signature);
  form.append("folder", sig.folder);
  const res = await fetch(`https://api.cloudinary.com/v1_1/${sig.cloud_name}/${sig.resource_type}/upload`, {
    method: "POST",
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.secure_url) throw new Error(data.error?.message || "Upload failed");
  return data.secure_url;
}

function Section({ title, children }) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
      <h2 className="font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function DisputeForm({ onSubmit, onCancel }) {
  const [reason, setReason] = useState("");
  const [proofs, setProofs] = useState([]);
  const [link, setLink] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function onFiles(e) {
    const files = [...(e.target.files || [])].slice(0, MAX_PROOFS - proofs.length);
    e.target.value = "";
    if (!files.length) return;
    setUploading(true);
    setError(null);
    try {
      const urls = [];
      for (const f of files) urls.push(await uploadProof(f));
      setProofs((p) => [...p, ...urls]);
    } catch (err) {
      setError(
        err.status === 503
          ? "File upload isn't available right now. Paste a link to your screenshot or photo instead."
          : err.message
      );
    } finally {
      setUploading(false);
    }
  }

  function addLink() {
    const url = link.trim();
    if (!/^https?:\/\/\S+$/i.test(url)) {
      setError("Paste a full link starting with https://");
      return;
    }
    setProofs((p) => [...p, url].slice(0, MAX_PROOFS));
    setLink("");
    setError(null);
  }

  async function submit(e) {
    e.preventDefault();
    if (!proofs.length) {
      setError("Attach at least one proof: a screenshot of the chat, a photo of the item, anything relevant.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSubmit({ reason: reason.trim(), proof_urls: proofs });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  const field =
    "w-full rounded-lg border border-border bg-surface px-3 py-2 text-base text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label htmlFor="dispute-reason" className="text-sm font-medium">What went wrong?</label>
      <textarea
        id="dispute-reason"
        required
        maxLength={2000}
        rows={3}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className={field}
      />
      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">Proof (required)</span>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={onFiles}
          disabled={uploading || proofs.length >= MAX_PROOFS}
          className="text-sm"
          aria-label="Upload screenshots or photos"
        />
        <div className="flex gap-2">
          <label htmlFor="proof-link" className="sr-only">Link to proof</label>
          <input
            id="proof-link"
            type="url"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            placeholder="or paste a link to a screenshot"
            className={cn(field, "h-11 py-0")}
          />
          <Button type="button" variant="outline" onClick={addLink} disabled={!link.trim()}>Add</Button>
        </div>
        {uploading && <p className="text-sm text-muted-foreground">Uploading…</p>}
        {proofs.length > 0 && (
          <ul className="flex flex-col gap-1 text-sm">
            {proofs.map((url, i) => (
              <li key={url + i} className="flex items-center justify-between gap-2">
                <a href={url} target="_blank" rel="noreferrer noopener" className="truncate text-primary underline">
                  Proof {i + 1}
                </a>
                <button
                  type="button"
                  onClick={() => setProofs((p) => p.filter((_, j) => j !== i))}
                  className="text-muted-foreground hover:underline"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Back</Button>
        <Button type="submit" disabled={busy || uploading || !reason.trim() || !proofs.length}>
          {busy ? "Sending…" : "Open dispute"}
        </Button>
      </div>
    </form>
  );
}

function RatingForm({ otherName, onSubmit }) {
  const [rating, setRating] = useState(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!rating) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit({ rating, comment: comment.trim() });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <p className="text-sm">How did it go with {otherName}? You can rate once, and your rating is public.</p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Rating">
        {RATINGS.map((r) => (
          <button
            key={r.value}
            type="button"
            role="radio"
            aria-checked={rating === r.value}
            onClick={() => setRating(r.value)}
            className={cn(
              "inline-flex h-11 items-center gap-2 rounded-lg border px-3 text-sm font-semibold",
              rating === r.value ? "border-ring ring-2 ring-ring" : "border-border",
              r.className
            )}
          >
            <span aria-hidden="true">{r.emoji}</span>
            {r.label}
          </button>
        ))}
      </div>
      <label htmlFor="rating-comment" className="sr-only">Comment</label>
      <textarea
        id="rating-comment"
        maxLength={1000}
        rows={2}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Add a comment"
        className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-base text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <div className="flex justify-end">
        <Button type="submit" disabled={busy || !rating}>{busy ? "Sending…" : "Submit rating"}</Button>
      </div>
    </form>
  );
}

export function TransactionPanel({ transactionId }) {
  const [tx, setTx] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [disputing, setDisputing] = useState(false);

  const load = useCallback(async () => {
    try {
      setTx(await clientApi(`/transactions/${transactionId}`));
    } catch {
      // The thread above already explains a missing or forbidden transaction.
    }
  }, [transactionId]);

  useEffect(() => {
    load();
    const poll = setInterval(load, 30000); // the other side's Complete / dispute shows up without a reload
    return () => clearInterval(poll);
  }, [load]);

  async function act(path, body) {
    setBusy(true);
    setError(null);
    try {
      setTx(await clientApi(`/transactions/${transactionId}/${path}`, { method: "POST", body }));
      return true;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setBusy(false);
    }
  }

  if (!tx) return null;
  const status = STATUS[tx.status] || STATUS.open;
  const otherName = (tx.role === "buyer" ? tx.seller : tx.buyer).full_name;
  const methods = tx.exchange_methods || [];

  return (
    <div className="flex flex-col gap-4">
      <Section title="Order summary">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Item</dt>
          <dd className="font-medium">{tx.listing.title}</dd>
          <dt className="text-muted-foreground">Agreed price</dt>
          <dd className="font-medium">{formatCAD(tx.amount)}</dd>
          <dt className="text-muted-foreground">Exchange</dt>
          <dd>{methods.length ? methods.map((m) => EXCHANGE[m] || m).join(", ") : "Agree in the chat below"}</dd>
          <dt className="text-muted-foreground">{tx.role === "buyer" ? "Seller" : "Buyer"}</dt>
          <dd>{otherName}</dd>
          <dt className="text-muted-foreground">Status</dt>
          <dd><Badge variant={status.variant}>{status.label}</Badge></dd>
        </dl>
        <p className="text-xs text-muted-foreground">
          BidCa doesn&apos;t handle money. You arrange the exchange directly with each other.
        </p>
      </Section>

      {tx.status === "open" && !disputing && (
        <Section title="Finish the deal">
          {tx.my_completed ? (
            <p className="text-sm" role="status">
              You marked this complete. Waiting for {otherName} to press Complete too.
            </p>
          ) : (
            <p className="text-sm">
              Press Complete once you&apos;re happy the deal is done. It completes only when you both press it.
              {tx.other_completed ? ` ${otherName} has already pressed it.` : ""}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => act("complete").catch(() => {})} disabled={busy || tx.my_completed}>
              {tx.my_completed ? "Waiting for the other side" : "Complete transaction"}
            </Button>
            <Button variant="outline" onClick={() => setDisputing(true)} disabled={busy}>Dispute</Button>
          </div>
        </Section>
      )}

      {tx.status === "open" && disputing && (
        <Section title="Open a dispute">
          <p className="text-sm text-muted-foreground">
            Our team reviews the proof from both sides and decides (for example a warning or a ban). Complete is
            disabled while the dispute is open.
          </p>
          <DisputeForm
            onSubmit={async (body) => {
              await act("dispute", body);
              setDisputing(false);
            }}
            onCancel={() => setDisputing(false)}
          />
        </Section>
      )}

      {tx.status === "disputed" && tx.dispute && (
        <Section title="Dispute open">
          <p className="text-sm">
            {tx.dispute.opened_by_me ? "You opened a dispute" : `${otherName} opened a dispute`}: {tx.dispute.reason}
          </p>
          <ul className="flex flex-wrap gap-3 text-sm">
            {tx.dispute.proof_urls.map((url, i) => (
              <li key={url + i}>
                <a href={url} target="_blank" rel="noreferrer noopener" className="text-primary underline">
                  Proof {i + 1}
                </a>
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">Complete is disabled until the dispute is closed.</p>
          {tx.dispute.opened_by_me && (
            <div>
              <Button variant="outline" onClick={() => act("cancel-dispute").catch(() => {})} disabled={busy}>
                Cancel dispute
              </Button>
              <p className="mt-1 text-xs text-muted-foreground">Sorted it out together? Cancelling reopens the deal.</p>
            </div>
          )}
        </Section>
      )}

      {tx.status === "cancelled" && (
        <Section title="Transaction cancelled">
          <p className="text-sm">
            {tx.cancelled_reason === "no_response"
              ? "The buyer didn't respond within 24 hours, so this sale was cancelled."
              : tx.dispute?.resolution?.note
                ? `Closed after review: ${tx.dispute.resolution.note}`
                : "This transaction was cancelled."}
          </p>
        </Section>
      )}

      {tx.status === "completed" && (
        <Section title={tx.can_rate ? `Rate ${otherName}` : "Completed"}>
          {tx.can_rate ? (
            <RatingForm
              otherName={otherName}
              onSubmit={async (body) => {
                await clientApi(`/transactions/${transactionId}/feedback`, { method: "POST", body });
                await load();
              }}
            />
          ) : (
            <p className="text-sm">
              Deal complete.
              {tx.my_feedback
                ? ` You rated ${otherName} ${RATINGS.find((r) => r.value === tx.my_feedback.rating)?.emoji || ""}.`
                : ""}
            </p>
          )}
        </Section>
      )}

      {error && !disputing && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
