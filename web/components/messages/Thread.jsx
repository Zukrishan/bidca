"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

import { Button } from "@/components/ui/button";
import { PUBLIC_API_URL } from "@/lib/config";
import { clientApi, getMe } from "@/lib/client-api";
import { cn } from "@/lib/utils";

const MAX = 2000;
const POLL_MS = 20000;

const timeFmt = new Intl.DateTimeFormat("en-CA", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const when = (iso) => timeFmt.format(new Date(iso));

/** Merge by _id, oldest first (live push, polling and our own sends can all deliver the same message). */
function merge(list, incoming) {
  const byId = new Map(list.map((m) => [m._id, m]));
  for (const m of incoming) byId.set(m._id, m);
  return [...byId.values()].sort((a, b) => a.created_at.localeCompare(b.created_at));
}

export function Thread({ transactionId }) {
  const [state, setState] = useState({ status: "loading" }); // loading | visitor | missing | error | ok
  const [data, setData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [me, setMe] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const d = await clientApi(`/transactions/${transactionId}/messages`);
      setData(d);
      setMessages((prev) => merge(prev, d.messages));
      setState({ status: "ok" });
    } catch (e) {
      setState((s) => {
        if (s.status === "ok") return s; // a failed poll keeps the thread on screen
        return { status: e.status === 401 ? "visitor" : e.status === 404 ? "missing" : "error" };
      });
    }
  }, [transactionId]);

  useEffect(() => {
    getMe().then(setMe, () => setMe(null));
    load();
    const poll = setInterval(load, POLL_MS);

    const socket = io(PUBLIC_API_URL, { path: "/api/socket.io", withCredentials: true });
    socket.on("connect", () => {
      socket.emitWithAck("join_user_notifications", {}).catch(() => {});
    });
    socket.on("message", (payload) => {
      if (payload?.transaction_id !== transactionId || !payload.message) return;
      setMessages((prev) => merge(prev, [payload.message]));
      load(); // marks it read, since this thread is open
    });
    return () => {
      clearInterval(poll);
      socket.disconnect();
    };
  }, [load, transactionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  async function send(e) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      const m = await clientApi(`/transactions/${transactionId}/messages`, { method: "POST", body: { body } });
      setMessages((prev) => merge(prev, [m]));
      setDraft("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  if (state.status === "loading") return <p className="text-muted-foreground">Loading…</p>;
  if (state.status === "visitor") {
    return (
      <p>
        <a href="/login" className="font-semibold text-primary underline">Sign in</a> to see this conversation.
      </p>
    );
  }
  if (state.status === "missing") {
    return (
      <p>
        Conversation not found. <Link href="/messages" className="font-semibold text-primary underline">Back to messages</Link>
      </p>
    );
  }
  if (state.status === "error") return <p className="text-destructive">Couldn&apos;t load this conversation. Try again shortly.</p>;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <Link href="/messages" className="text-sm text-muted-foreground hover:underline">&larr; All messages</Link>

      <div className="flex items-center gap-3 rounded-lg border border-border bg-surface p-3">
        <div className="size-14 shrink-0 overflow-hidden rounded-lg bg-muted">
          {data.listing.image && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={data.listing.image} alt="" className="h-full w-full object-cover" />
          )}
        </div>
        <div className="min-w-0">
          <a href={`/auctions/${data.listing.id}`} className="block truncate font-semibold hover:underline">
            {data.listing.title}
          </a>
          <p className="text-sm text-muted-foreground">
            {data.other_party.full_name}
            {data.other_party.city ? ` · ${data.other_party.city}` : ""}
          </p>
        </div>
      </div>

      <ul className="flex min-h-48 flex-col gap-2" aria-live="polite">
        {messages.length === 0 && (
          <li className="text-muted-foreground">No messages yet. Say hello and agree a time and place for pickup.</li>
        )}
        {messages.map((m) => {
          const mine = me && m.sender_id === me._id;
          return (
            <li key={m._id} className={cn("flex flex-col", mine ? "items-end" : "items-start")}>
              {/* Plain text only: React escapes it, whitespace is preserved with CSS. */}
              <p
                className={cn(
                  "max-w-[85%] whitespace-pre-wrap break-words rounded-lg px-3 py-2",
                  mine ? "bg-primary text-primary-foreground" : "border border-border bg-surface"
                )}
              >
                {m.body}
              </p>
              <span className="mt-0.5 text-xs text-muted-foreground">{when(m.created_at)}</span>
            </li>
          );
        })}
        <div ref={bottomRef} />
      </ul>

      <form onSubmit={send} className="flex flex-col gap-2">
        <label htmlFor="message-body" className="sr-only">Message</label>
        <textarea
          id="message-body"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={MAX}
          rows={3}
          placeholder="Write a message"
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-base text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end">
          <Button type="submit" disabled={sending || !draft.trim()}>{sending ? "Sending…" : "Send"}</Button>
        </div>
      </form>
    </div>
  );
}
